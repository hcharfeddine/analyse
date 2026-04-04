"""
Enhanced affiliation extraction from multiple sources.
"""

import asyncio
import re
import logging
from typing import List, Dict, Optional, Set
import aiohttp

logger = logging.getLogger(__name__)


class OrcidAffiliationExtractor:
    """Extract verified affiliations from ORCID using public API."""
    
    BASE_URL = "https://pub.orcid.org/v3.0"
    
    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def search_by_name(self, author_name: str) -> List[str]:
        """Search ORCID for author by name and extract affiliations."""
        if not author_name or not self.session:
            return []
        
        try:
            search_url = f"{self.BASE_URL}/search"
            params = {
                'q': f'given-name:"{author_name.split()[0]}" AND family-name:"{author_name.split()[-1]}"'
            }
            
            async with self.session.get(
                search_url, 
                params=params, 
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    return []
                
                data = await resp.json()
                results = data.get('result', [])
                
                if not results:
                    return []
                
                orcid_id = results[0].get('orcid-identifier', {}).get('path')
                if not orcid_id:
                    return []
                
                profile_url = f"{self.BASE_URL}/{orcid_id}/employments"
                async with self.session.get(
                    profile_url,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as profile_resp:
                    if profile_resp.status != 200:
                        return []
                    
                    profile_data = await profile_resp.json()
                    affiliations = []
                    
                    employments = profile_data.get('employment-summary', [])
                    for emp in employments:
                        org_name = emp.get('organization', {}).get('name')
                        if org_name:
                            affiliations.append(org_name)
                    
                    return affiliations
        
        except Exception as e:
            logger.debug(f"ORCID lookup failed for {author_name}: {e}")
            return []


class RORAffiliationExtractor:
    """Extract official institution data (country, type) from Research Organization Registry (ROR)."""
    
    BASE_URL = "https://api.ror.org/v2/organizations"
    
    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Academic Research Tool/1.0',
            'Accept': 'application/json'
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def lookup_affiliation(self, affiliation_str: str) -> Optional[Dict]:
        """Query ROR for an affiliation string and return metadata."""
        if not affiliation_str or not self.session:
            return None
            
        try:
            async with self.session.get(
                self.BASE_URL,
                params={'affiliation': affiliation_str},
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    return None
                    
                data = await resp.json()
                items = data.get('items', [])
                
                if not items:
                    return None
                
                top_match = items[0].get('organization', {})
                if not top_match:
                    return None
                    
                org_types = top_match.get('types', [])
                org_type = org_types[0] if org_types else "Other"
                
                country = "N/A"
                locations = top_match.get('locations', [])
                geonames = locations[0].get('geonames_details', {})
                country = geonames.get('country_name') or locations[0].get('country_name')
                
                if not country or country == "N/A":
                    country_obj = top_match.get('country', {})
                    if isinstance(country_obj, dict):
                        country = country_obj.get('country_name') or country_obj.get('name')
                    elif isinstance(country_obj, str):
                        country = country_obj

                ror_id = top_match.get('id')
                
                return {
                    'ror_id': ror_id,
                    'name': top_match.get('names', [{}])[0].get('value') if top_match.get('names') else None,
                    'type': org_type.capitalize(),
                    'country': country or "N/A"
                }
                
        except Exception as e:
            logger.debug(f"ROR lookup failed for {affiliation_str}: {e}")
            return None


class AffiliationAggregator:
    """Intelligently aggregate and validate affiliations from multiple sources."""
    
    INSTITUTION_ALIASES = {
        'mit': ['massachusetts institute of technology', 'mit'],
        'stanford': ['stanford university', 'stanford'],
        'harvard': ['harvard university', 'harvard'],
        'berkeley': ['uc berkeley', 'university of california berkeley', 'ucb'],
        'cmu': ['carnegie mellon university', 'carnegie mellon', 'cmu'],
        'oxford': ['university of oxford', 'oxford university', 'oxford'],
        'cambridge': ['university of cambridge', 'cambridge university', 'cambridge'],
    }
    
    def __init__(self):
        self.orcid_extractor = None
        self.ror_extractor = None

    async def __aenter__(self):
        self.orcid_extractor = OrcidAffiliationExtractor()
        await self.orcid_extractor.__aenter__()
        self.ror_extractor = RORAffiliationExtractor()
        await self.ror_extractor.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.orcid_extractor:
            await self.orcid_extractor.__aexit__(exc_type, exc_val, exc_tb)
        if self.ror_extractor:
            await self.ror_extractor.__aexit__(exc_type, exc_val, exc_tb)
    
    async def aggregate_affiliations(
        self, 
        author_name: str,
        sources: Dict[str, List[str]]
    ) -> List[str]:
        """Aggregate affiliations from multiple sources with deduplication."""
        all_affiliations = []
        source_confidence = {
            'orcid': 5,
            'crossref': 4,
            'arxiv': 4,
            'semantic_scholar': 3,
            'grobid': 3,
            'researchgate': 2,
        }
        
        try:
            orcid_affs = await self.orcid_extractor.search_by_name(author_name)
            if orcid_affs:
                sources['orcid'] = orcid_affs
        except:
            pass
        
        scored_affiliations: Dict[str, int] = {}
        for source_name, affiliations in sources.items():
            confidence = source_confidence.get(source_name, 1)
            for aff in affiliations:
                aff_clean = self._normalize_affiliation(aff)
                if aff_clean and len(aff_clean) > 4:
                    if aff_clean not in scored_affiliations:
                        scored_affiliations[aff_clean] = 0
                    scored_affiliations[aff_clean] += confidence
        
        sorted_affs = sorted(
            scored_affiliations.items(),
            key=lambda x: (-x[1], x[0])
        )
        
        deduplicated = self._deduplicate_similar_affiliations(
            [aff for aff, score in sorted_affs]
        )
        
        return deduplicated[:5]

    async def enrich_paper_with_ror(self, paper) -> None:
        """Enrich paper object with aggregated ROR data from all author affiliations."""
        if not paper.authors or not self.ror_extractor:
            return

        # Collect unique affiliations across all authors
        unique_affiliations = set()
        for author in paper.authors:
            for aff in author.affiliations:
                if aff and aff != "N/A":
                    unique_affiliations.add(aff)
        
        if not unique_affiliations:
            return

        ror_ids = []
        countries = []
        org_types = []
        seen_ror_ids = set()

        # Lookup ROR for each unique affiliation
        for aff in unique_affiliations:
            ror_data = await self.ror_extractor.lookup_affiliation(aff)
            if ror_data:
                rid = ror_data.get('ror_id')
                if rid and rid not in seen_ror_ids:
                    seen_ror_ids.add(rid)
                    ror_ids.append(rid)
                    
                    country = ror_data.get('country')
                    if country and country not in countries:
                        countries.append(country)
                        
                    org_type = ror_data.get('type')
                    if org_type and org_type not in org_types:
                        org_types.append(org_type)

        # Update paper-level fields
        paper.ror_ids = ror_ids
        paper.countries = countries
        paper.organization_types = org_types

    def _normalize_affiliation(self, affiliation: str) -> str:
        """Normalize affiliation string for comparison."""
        if not affiliation:
            return ""
        
        aff = ' '.join(affiliation.split())
        aff_lower = aff.lower()
        
        for canonical, aliases in self.INSTITUTION_ALIASES.items():
            if any(alias.lower() in aff_lower for alias in aliases):
                return canonical.title()
        
        aff = re.sub(r'\s+(Department|School|College|Faculty|Institute|Center|Laboratory)(?:\s+of)?', '', aff, flags=re.I)
        aff = re.sub(r'[,;|].*$', '', aff)
        aff = re.sub(r'@[\w\.\-]+$', '', aff)
        
        return aff.strip()
    
    def _deduplicate_similar_affiliations(self, affiliations: List[str]) -> List[str]:
        """Remove similar/duplicate affiliations using fuzzy matching."""
        if not affiliations:
            return []
        
        unique = []
        for aff in affiliations:
            is_duplicate = False
            for existing in unique:
                if (aff.lower() in existing.lower() or 
                    existing.lower() in aff.lower()):
                    is_duplicate = True
                    break
                if self._similarity_ratio(aff, existing) > 0.85:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique.append(aff)
        
        return unique
    
    @staticmethod
    def _similarity_ratio(s1: str, s2: str) -> float:
        """Calculate similarity ratio between two strings."""
        s1_lower = s1.lower()
        s2_lower = s2.lower()
        
        if s1_lower in s2_lower or s2_lower in s1_lower:
            return 0.9
        
        matches = sum(1 for c1, c2 in zip(s1_lower, s2_lower) if c1 == c2)
        total = max(len(s1), len(s2))
        
        return matches / total if total > 0 else 0

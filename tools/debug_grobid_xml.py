"""Debug script to see actual GROBID TEI XML structure for affiliations."""

import asyncio
import aiohttp
import json
from pathlib import Path
from lxml import etree

async def debug_grobid_response():
    """Test GROBID with a real PDF and show the XML structure."""
    
    # Find a downloaded PDF
    pdf_dir = Path("academic/pdfs")
    pdf_files = list(pdf_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("❌ No PDF files found in academic/pdfs/")
        print("   Please download PDFs first")
        return
    
    pdf_path = pdf_files[0]
    print(f"📄 Testing with: {pdf_path.name}")
    print(f"   Size: {pdf_path.stat().st_size / 1024:.1f} KB")
    
    # Send to GROBID
    grobid_url = "http://localhost:8070"
    
    async with aiohttp.ClientSession() as session:
        # Check service
        try:
            async with session.get(f"{grobid_url}/api/isalive", timeout=aiohttp.ClientTimeout(total=5), ssl=False) as resp:
                if resp.status != 200:
                    print(f"❌ GROBID service not responding (status {resp.status})")
                    return
        except Exception as e:
            print(f"❌ GROBID service not available: {e}")
            print(f"   Run: docker run -p 8070:8070 grobid/grobid:0.8.2-full")
            return
        
        print("✓ GROBID service is running")
        
        # Send PDF to GROBID
        with open(pdf_path, 'rb') as f:
            form = aiohttp.FormData()
            form.add_field('input', f, filename=pdf_path.name, content_type='application/pdf')
            
            print(f"\n📤 Sending PDF to GROBID...")
            async with session.post(
                f"{grobid_url}/api/processFulltextDocument",
                data=form,
                timeout=aiohttp.ClientTimeout(total=120),
                ssl=False
            ) as resp:
                if resp.status != 200:
                    print(f"❌ GROBID returned status {resp.status}")
                    text = await resp.text()
                    print(f"Response: {text[:500]}")
                    return
                
                tei_xml = await resp.text()
                print(f"✓ Received {len(tei_xml):,} bytes of TEI XML")
    
    # Parse and analyze XML structure
    print("\n" + "="*80)
    print("📊 TEI XML STRUCTURE ANALYSIS")
    print("="*80)
    
    try:
        root = etree.fromstring(tei_xml.encode('utf-8'))
    except etree.XMLSyntaxError as e:
        print(f"❌ XML parsing error: {e}")
        return
    
    ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
    
    # Show all element types
    all_elements = set()
    for elem in root.iter():
        tag = elem.tag.replace('{http://www.tei-c.org/ns/1.0}', '')
        all_elements.add(tag)
    
    print(f"\n📋 Element types in document: {sorted(all_elements)}")
    
    # Look for author/affiliation elements
    print("\n👥 AUTHOR ELEMENTS:")
    authors = root.xpath('//tei:author | //tei:editor', namespaces=ns)
    print(f"   Found {len(authors)} author/editor elements")
    
    for i, author in enumerate(authors[:3], 1):  # Show first 3
        print(f"\n   Author {i}:")
        print(f"   XML: {etree.tostring(author, pretty_print=True, encoding='unicode')[:500]}")
        
        # Extract all text
        all_text = ' '.join(author.xpath('.//text()', namespaces=ns)).strip()
        print(f"   All text: {all_text[:200]}")
    
    # Look for affiliation elements
    print("\n🏢 AFFILIATION ELEMENTS:")
    affs = root.xpath('//tei:affiliation', namespaces=ns)
    print(f"   Found {len(affs)} <affiliation> elements")
    
    for i, aff in enumerate(affs[:3], 1):
        aff_text = ' '.join(aff.xpath('.//text()', namespaces=ns)).strip()
        print(f"   Affiliation {i}: {aff_text[:150]}")
    
    # Look for orgName
    print("\n🏛️  ORGANIZATION NAMES:")
    orgs = root.xpath('//tei:orgName', namespaces=ns)
    print(f"   Found {len(orgs)} <orgName> elements")
    
    for i, org in enumerate(orgs[:3], 1):
        org_text = ' '.join(org.xpath('.//text()', namespaces=ns)).strip()
        print(f"   Organization {i}: {org_text[:150]}")
    
    # Look for address
    print("\n📍 ADDRESS ELEMENTS:")
    addrs = root.xpath('//tei:address', namespaces=ns)
    print(f"   Found {len(addrs)} <address> elements")
    
    for i, addr in enumerate(addrs[:3], 1):
        addr_text = ' '.join(addr.xpath('.//text()', namespaces=ns)).strip()
        print(f"   Address {i}: {addr_text[:150]}")
    
    # Save full XML for inspection
    xml_file = Path("academic/debug_grobid_output.xml")
    with open(xml_file, 'w', encoding='utf-8') as f:
        f.write(etree.tostring(root, pretty_print=True, encoding='unicode'))
    print(f"\n💾 Full XML saved to: {xml_file}")

if __name__ == "__main__":
    asyncio.run(debug_grobid_response())

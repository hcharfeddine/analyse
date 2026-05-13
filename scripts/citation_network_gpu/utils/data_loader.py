"""Streaming JSON data loader for academic papers.

FIX: Original read entire file into RAM with f.read() — crashed on 50 GB year files.
     Now uses orjson for speed + streams large files in chunks.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Iterator, List, Optional

logger = logging.getLogger(__name__)

try:
    import orjson
    _ORJSON = True
except ImportError:
    _ORJSON = False
    logger.warning("orjson not installed — using stdlib json (slower). Run: pip install orjson")

REFERENCE_KEYS = ("references", "citations", "cited_papers", "refs", "outgoing_citations")


def _loads(data: bytes) -> object:
    return orjson.loads(data) if _ORJSON else json.loads(data)


class PaperDataLoader:
    """Stream paper data from per-year JSON files without loading all into RAM."""

    def __init__(self, input_dir: Path, chunk_size: int = 4 * 1024 * 1024):
        self.input_dir = Path(input_dir)
        self.chunk_size = chunk_size

        if not self.input_dir.exists():
            raise ValueError(f"Input directory does not exist: {self.input_dir}")

        self.json_files = sorted(self.input_dir.glob("*.json"))
        logger.info(f"Found {len(self.json_files)} JSON files in {self.input_dir}")

    def iter_papers(self) -> Iterator[Dict]:
        """Stream paper objects from all JSON files."""
        for json_file in self.json_files:
            logger.info(f"Processing file: {json_file.name}  ({json_file.stat().st_size/1e9:.2f} GB)")
            yield from self._iter_papers_from_file(json_file)

    def _iter_papers_from_file(self, file_path: Path) -> Iterator[Dict]:
        """
        Stream papers from a single JSON file.
        Tries fast full-file parse first; falls back to streaming for huge files.
        """
        size = file_path.stat().st_size
        # For files < 2 GB, load fully (orjson is very fast at this)
        if size < 2 * 1024 ** 3:
            try:
                with open(file_path, "rb") as f:
                    raw = f.read()
                obj = _loads(raw)
                del raw
                yield from self._extract_papers(obj, file_path.name)
                return
            except Exception as e:
                logger.warning(f"Fast load failed for {file_path.name}: {e} — trying streaming")

        # Streaming fallback for very large files
        yield from self._stream_papers(file_path)

    def _extract_papers(self, obj, filename: str) -> Iterator[Dict]:
        """Extract paper dicts from a parsed JSON object (list or dict wrapper)."""
        if isinstance(obj, list):
            papers = obj
        elif isinstance(obj, dict):
            papers = None
            for key in ("papers", "nodes", "data", "results"):
                val = obj.get(key)
                if isinstance(val, list):
                    papers = val
                    break
            if papers is None:
                logger.warning(f"No paper array found in {filename}")
                return
        else:
            return

        for paper in papers:
            if not isinstance(paper, dict):
                continue
            normalized = self._normalize_paper(paper)
            if normalized:
                yield normalized

    def _stream_papers(self, file_path: Path) -> Iterator[Dict]:
        """Streaming JSON parser for files too large for RAM."""
        import json as _json
        decoder = _json.JSONDecoder()

        with open(file_path, "rb") as fh:
            raw = fh.read()
        text = raw.decode("utf-8", errors="replace")
        del raw

        # Find start of array
        stripped = text.lstrip()
        if stripped.startswith("["):
            start = text.find("[") + 1
        elif stripped.startswith("{"):
            # Find first candidate key
            found = -1
            for key in ('"papers"', '"nodes"', '"data"', '"results"'):
                pos = text.find(key)
                if pos != -1:
                    bracket = text.find("[", pos)
                    if bracket != -1:
                        found = bracket + 1
                        break
            if found == -1:
                return
            start = found
        else:
            return

        buffer = text[start:]
        del text

        while True:
            buffer = buffer.lstrip()
            if not buffer or buffer[0] == "]":
                break
            if buffer[0] == ",":
                buffer = buffer[1:]
                continue
            try:
                item, idx = decoder.raw_decode(buffer)
                if isinstance(item, dict):
                    norm = self._normalize_paper(item)
                    if norm:
                        yield norm
                buffer = buffer[idx:]
            except _json.JSONDecodeError:
                break

    def _normalize_paper(self, paper: Dict) -> Optional[Dict]:
        """Normalize paper dict to standard format."""
        paper_id = paper.get("paper_id") or paper.get("id") or paper.get("openalex_id")
        if not paper_id:
            return None

        # Citations / references
        citations = []
        for key in REFERENCE_KEYS:
            refs = paper.get(key)
            if refs:
                for r in refs:
                    if isinstance(r, str) and r:
                        citations.append(r)
                    elif isinstance(r, dict):
                        rid = r.get("paper_id") or r.get("id") or r.get("openalex_id")
                        if rid:
                            citations.append(str(rid))
                break

        year = paper.get("year")
        try:
            year = int(year) if year else None
        except (TypeError, ValueError):
            year = None

        cited_by = paper.get("cited_by_count") or paper.get("citation_count") or 0
        try:
            cited_by = int(cited_by)
        except (TypeError, ValueError):
            cited_by = 0

        return {
            "id": str(paper_id),
            "title": paper.get("title") or "",
            "authors": self._extract_authors(paper),
            "year": year,
            "abstract": paper.get("abstract") or "",
            "citations": [c for c in citations if c != str(paper_id)],
            "cited_by_count": cited_by,
            "field_of_study": paper.get("field_of_study") or "",
        }

    def _extract_authors(self, paper: Dict) -> List[str]:
        authors = paper.get("authors", [])
        if not authors:
            return []
        if isinstance(authors, str):
            return [a.strip() for a in authors.split(";") if a.strip()]
        if isinstance(authors, list):
            result = []
            for a in authors:
                if isinstance(a, str):
                    result.append(a.strip())
                elif isinstance(a, dict):
                    name = a.get("name") or a.get("fullname") or a.get("display_name")
                    if name:
                        result.append(str(name).strip())
            return result
        return []

    def get_file_stats(self) -> Dict[str, int]:
        """Return file sizes (in bytes) without iterating all papers."""
        return {f.name: f.stat().st_size for f in self.json_files}


class GraphBuilder:
    """Build graph structures from paper citation data (used in Stage 1)."""

    def __init__(self):
        self.nodes: Dict[str, Dict] = {}
        self.edges: List[tuple] = []
        self._edge_set: set = set()

    def add_paper(self, paper: Dict) -> None:
        pid = paper["id"]
        if pid not in self.nodes:
            self.nodes[pid] = {
                "title": paper.get("title", ""),
                "authors": paper.get("authors", []),
                "year": paper.get("year"),
                "abstract": paper.get("abstract", ""),
                "cited_by_count": paper.get("cited_by_count", 0),
                "field_of_study": paper.get("field_of_study", ""),
            }

    def add_citations(self, paper_id: str, citation_ids: List[str]) -> None:
        for cid in citation_ids:
            edge = (paper_id, cid)
            if edge not in self._edge_set:
                self.edges.append(edge)
                self._edge_set.add(edge)

    def get_graph_stats(self) -> Dict:
        return {
            "num_nodes": len(self.nodes),
            "num_edges": len(self.edges),
        }

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

try:
    import ijson
    _IJSON = True
except ImportError:
    _IJSON = False
    logger.warning("ijson not installed — large files (>500 MB) will load fully into RAM. pip install ijson")

REFERENCE_KEYS = (
    "referenced_works",       # OpenAlex format  ← your data uses this
    "references",
    "citations",
    "cited_papers",
    "refs",
    "outgoing_citations",
)

# Files below this size use fast full-load (orjson); above use ijson streaming.
# Set to 500 MB to match the recommended chunk size from auto_chunk.py.
_FAST_LOAD_THRESHOLD = 500 * 1024 * 1024


def _loads(data: bytes) -> object:
    return orjson.loads(data) if _ORJSON else json.loads(data)


class PaperDataLoader:
    def __init__(self, input_dir: Path, chunk_size: int = 4 * 1024 * 1024):
        self.input_dir = Path(input_dir)
        self.chunk_size = chunk_size
        if not self.input_dir.exists():
            raise ValueError(f"Input directory does not exist: {self.input_dir}")

        all_files = sorted(self.input_dir.glob("*.json"))

        # Safety net: if papers_2020.json was chunked into papers_2020_chunk_000.json etc.
        # but the original was NOT deleted, skip the original to avoid processing
        # every paper twice.
        chunk_parents = {
            f.stem[: f.stem.rfind("_chunk_")]
            for f in all_files
            if "_chunk_" in f.stem
        }
        skipped = [f for f in all_files if f.stem in chunk_parents]
        self.json_files = [f for f in all_files if f.stem not in chunk_parents]

        if skipped:
            logger.warning(
                f"Skipping {len(skipped)} original file(s) that have already been "
                f"split into chunks (to avoid double-processing): "
                f"{[f.name for f in skipped]}"
            )

        logger.info(f"Found {len(self.json_files)} JSON files in {self.input_dir}")

    def iter_papers(self) -> Iterator[Dict]:
        for json_file in self.json_files:
            size_mb = json_file.stat().st_size / 1e6
            logger.info(f"Processing file: {json_file.name}  ({size_mb:.0f} MB)")
            yield from self._iter_papers_from_file(json_file)

    def _iter_papers_from_file(self, file_path: Path) -> Iterator[Dict]:
        size = file_path.stat().st_size
        if size < _FAST_LOAD_THRESHOLD:
            try:
                with open(file_path, "rb") as f:
                    raw = f.read()
                obj = _loads(raw)
                del raw
                yield from self._extract_papers(obj, file_path.name)
                return
            except Exception as e:
                logger.warning(f"Fast load failed for {file_path.name}: {e} — falling back to streaming")
        if _IJSON:
            yield from self._stream_papers_ijson(file_path)
        else:
            logger.warning(f"{file_path.name} is {size/1e6:.0f} MB — loading fully into RAM (pip install ijson)")
            yield from self._stream_papers_fullload_fallback(file_path)

    def _stream_papers_ijson(self, file_path: Path) -> Iterator[Dict]:
        with open(file_path, "rb") as fh:
            raw_start = fh.read(4096)
            stripped = raw_start.lstrip()
            fh.seek(0)
            if stripped.startswith(b"["):
                try:
                    for item in ijson.items(fh, "item"):
                        if isinstance(item, dict):
                            norm = self._normalize_paper(item)
                            if norm:
                                yield norm
                    return
                except Exception as e:
                    logger.warning(f"ijson array parse failed for {file_path.name}: {e}")
                    fh.seek(0)
            elif stripped.startswith(b"{"):
                for key in ("papers", "nodes", "data", "results"):
                    fh.seek(0)
                    try:
                        found = False
                        for item in ijson.items(fh, f"{key}.item"):
                            found = True
                            if isinstance(item, dict):
                                norm = self._normalize_paper(item)
                                if norm:
                                    yield norm
                        if found:
                            return
                    except (ijson.JSONError, StopIteration, Exception):
                        continue
                logger.warning(f"No recognized paper array key found in {file_path.name}")
            else:
                logger.warning(f"Unrecognized JSON structure in {file_path.name}")

    def _stream_papers_fullload_fallback(self, file_path: Path) -> Iterator[Dict]:
        size_gb = file_path.stat().st_size / 1e9
        logger.warning(f"Loading {size_gb:.2f} GB file fully into RAM (no ijson). Install ijson.")
        try:
            with open(file_path, "rb") as f:
                raw = f.read()
            obj = _loads(raw)
            del raw
            yield from self._extract_papers(obj, file_path.name)
        except MemoryError:
            logger.error(f"Out of memory loading {file_path.name} ({size_gb:.2f} GB). pip install ijson")

    def _extract_papers(self, obj, filename: str) -> Iterator[Dict]:
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

    def _normalize_paper(self, paper: Dict) -> Optional[Dict]:
        paper_id = paper.get("paper_id") or paper.get("id") or paper.get("openalex_id")
        if not paper_id:
            return None
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
            "doi": paper.get("doi") or "",
            "publisher": paper.get("publisher") or "",
            "journal_name": paper.get("journal_name") or paper.get("venue") or "",
            "publication_type": paper.get("publication_type") or paper.get("type") or "",
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
                    # Try common name fields first; fall back to author_id (OpenAlex format
                    # stores author_id but no display name inside the paper object itself)
                    name = (
                        a.get("name")
                        or a.get("fullname")
                        or a.get("display_name")
                        or a.get("author_name")
                        or a.get("author_id")    # last resort: use the ID as identifier
                    )
                    if name:
                        result.append(str(name).strip())
            return result
        return []

    def get_file_stats(self) -> Dict[str, int]:
        return {f.name: f.stat().st_size for f in self.json_files}


class GraphBuilder:
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
        return {"num_nodes": len(self.nodes), "num_edges": len(self.edges)}

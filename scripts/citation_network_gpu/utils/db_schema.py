import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


def create_optimized_schema(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-512000")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA wal_autocheckpoint=50000")
    conn.execute("PRAGMA locking_mode=EXCLUSIVE")
    conn.execute("PRAGMA busy_timeout=5000")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paper_id_mapping (
            node_id INTEGER PRIMARY KEY,
            paper_id TEXT UNIQUE NOT NULL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_paper_id_mapping_paper_id ON paper_id_mapping(paper_id)")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS field_of_study_mapping (
            field_id INTEGER PRIMARY KEY,
            field_name TEXT UNIQUE NOT NULL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_field_mapping_name ON field_of_study_mapping(field_name)")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS graph_nodes (
            node_id INTEGER PRIMARY KEY,
            year INTEGER,
            field_id INTEGER,
            in_degree INTEGER DEFAULT 0,
            out_degree INTEGER DEFAULT 0
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_graph_nodes_year ON graph_nodes(year)")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS graph_edges (
            source_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            PRIMARY KEY (source_id, target_id)
        ) WITHOUT ROWID
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_graph_edges_source ON graph_edges(source_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_graph_edges_target ON graph_edges(target_id)")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paper_metadata (
            node_id INTEGER PRIMARY KEY,
            paper_id TEXT UNIQUE NOT NULL,
            title TEXT,
            authors TEXT,
            abstract TEXT,
            cited_by_count INTEGER DEFAULT 0,
            doi TEXT,
            publisher TEXT,
            journal_name TEXT,
            publication_type TEXT
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_paper_metadata_paper_id ON paper_metadata(paper_id)")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processing_status (
            stage TEXT PRIMARY KEY,
            status TEXT,
            timestamp TEXT,
            details TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS node_coordinates (
            node_id INTEGER PRIMARY KEY,
            x REAL,
            y REAL,
            layout_iteration INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processed_files (
            filename TEXT PRIMARY KEY,
            papers INTEGER,
            edges INTEGER,
            finished_at TEXT
        )
    """)

    conn.commit()
    logger.info(f"Created optimized database schema at {db_path}")
    return conn


def reset_database(db_path: Path) -> None:
    if db_path.exists():
        db_path.unlink()
        for suffix in ("-wal", "-shm"):
            p = Path(str(db_path) + suffix)
            if p.exists():
                p.unlink()
        logger.info(f"Reset database: {db_path}")

import logging
import sqlite3
import threading
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class NodeMapping:
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.paper_to_node: Dict[str, int] = {}
        self.node_to_paper: Dict[int, str] = {}
        self.next_node_id = 0
        self._lock = threading.RLock() 

    def ensure_tables(self, conn: sqlite3.Connection) -> None:
        """Create mapping tables if they don't exist."""
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS paper_id_mapping (
                node_id INTEGER PRIMARY KEY,
                paper_id TEXT UNIQUE NOT NULL
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_paper_id_mapping_paper_id
            ON paper_id_mapping(paper_id)
        """)

        conn.commit()

    def load_mappings(self, conn: sqlite3.Connection) -> None:
        """Load existing mappings from database into memory cache."""
        cursor = conn.cursor()
        rows = cursor.execute("SELECT node_id, paper_id FROM paper_id_mapping").fetchall()

        self.paper_to_node.clear()
        self.node_to_paper.clear()
        self.next_node_id = 0

        for node_id, paper_id in rows:
            self.paper_to_node[paper_id] = node_id
            self.node_to_paper[node_id] = paper_id
            if node_id >= self.next_node_id:
                self.next_node_id = node_id + 1

        if rows:
            logger.info(f"Loaded {len(rows):,} existing paper ID mappings")

    def get_or_create_node_id(self, paper_id: str) -> int:
        with self._lock:
            if paper_id in self.paper_to_node:
                return self.paper_to_node[paper_id]

            node_id = self.next_node_id
            self.next_node_id += 1
            self.paper_to_node[paper_id] = node_id
            self.node_to_paper[node_id] = paper_id
            return node_id

    def get_node_id(self, paper_id: str) -> Optional[int]:
        """Get node_id if it exists, None otherwise."""
        return self.paper_to_node.get(paper_id)

    def get_paper_id(self, node_id: int) -> Optional[str]:
        """Get paper_id if it exists, None otherwise."""
        return self.node_to_paper.get(node_id)

    def flush_to_db(self, conn: sqlite3.Connection, batch_size: int = 10000) -> int:
        with self._lock:
            all_mappings = list(self.node_to_paper.items())  # snapshot while locked

        cursor = conn.cursor()
        total_inserted = 0

        for i in range(0, len(all_mappings), batch_size):
            batch = all_mappings[i : i + batch_size]
            cursor.executemany(
                "INSERT OR IGNORE INTO paper_id_mapping (node_id, paper_id) VALUES (?, ?)",
                batch,
            )
            total_inserted += cursor.rowcount

        conn.commit()
        logger.info(
            f"Flushed {len(all_mappings):,} mappings to DB "
            f"({total_inserted:,} new, {len(all_mappings) - total_inserted:,} already existed)"
        )
        return total_inserted

    def stats(self) -> Dict:
        """Return mapping statistics."""
        return {
            "total_mappings": len(self.paper_to_node),
           "next_node_id": self.next_node_id,
        } 


class FieldMapping:
    

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.field_to_id: Dict[str, int] = {}
        self.id_to_field: Dict[int, str] = {}
        self.next_field_id = 0
        self._lock = threading.RLock()

    def ensure_tables(self, conn: sqlite3.Connection) -> None:
        """Create mapping tables if they don't exist."""
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS field_of_study_mapping (
                field_id INTEGER PRIMARY KEY,
                field_name TEXT UNIQUE NOT NULL
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_field_mapping_name
            ON field_of_study_mapping(field_name)
        """)

        conn.commit()

    def load_mappings(self, conn: sqlite3.Connection) -> None:
        """Load existing mappings from database into memory cache."""
        cursor = conn.cursor()
        rows = cursor.execute("SELECT field_id, field_name FROM field_of_study_mapping").fetchall()

        self.field_to_id.clear()
        self.id_to_field.clear()
        self.next_field_id = 0

        for field_id, field_name in rows:
            self.field_to_id[field_name] = field_id
            self.id_to_field[field_id] = field_name
            if field_id >= self.next_field_id:
                self.next_field_id = field_id + 1

        if rows:
            logger.info(f"Loaded {len(rows):,} existing field mappings")

    def get_or_create_field_id(self, field_name: str) -> int:
       
        if not field_name:
            return -1  # Special ID for empty/unknown field

        with self._lock:
            if field_name in self.field_to_id:
                return self.field_to_id[field_name]

            field_id = self.next_field_id
            self.next_field_id += 1
            self.field_to_id[field_name] = field_id
            self.id_to_field[field_id] = field_name
            return field_id

    def get_field_id(self, field_name: str) -> Optional[int]:
        """Get field_id if it exists, None otherwise."""
        return self.field_to_id.get(field_name)

    def get_field_name(self, field_id: int) -> Optional[str]:
        """Get field name if it exists, None otherwise."""
        return self.id_to_field.get(field_id)

    def flush_to_db(self, conn: sqlite3.Connection, batch_size: int = 10000) -> int:
       
        with self._lock:
            all_mappings = list(self.id_to_field.items())  # snapshot while locked

        cursor = conn.cursor()
        total_inserted = 0

        for i in range(0, len(all_mappings), batch_size):
            batch = all_mappings[i : i + batch_size]
            cursor.executemany(
                "INSERT OR IGNORE INTO field_of_study_mapping (field_id, field_name) VALUES (?, ?)",
                batch,
            )
            total_inserted += cursor.rowcount

        conn.commit()
        logger.info(
            f"Flushed {len(all_mappings):,} field mappings to DB "
            f"({total_inserted:,} new, {len(all_mappings) - total_inserted:,} already existed)"
        )
        return total_inserted

    def stats(self) -> Dict:
        """Return mapping statistics."""
        return {
            "total_fields": len(self.field_to_id),
            "next_field_id": self.next_field_id,
        }

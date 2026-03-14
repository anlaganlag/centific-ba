import sqlite3
import json
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
import os
import uuid


class DatabaseService:
    """SQLite database service for BA Toolkit"""

    def __init__(self, db_path: str = "data/app.db"):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        # Skip directory creation for in-memory database
        if db_path != ":memory:":
            db_dir = os.path.dirname(db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
        self.init_database()

    def _get_conn(self) -> sqlite3.Connection:
        # For in-memory DB, reuse the same connection (otherwise each connect creates new DB)
        if self.db_path == ":memory:":
            if self._conn is None:
                self._conn = sqlite3.connect(self.db_path)
                self._conn.row_factory = sqlite3.Row
                self._conn.execute("PRAGMA foreign_keys = ON")
            return self._conn

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _close_conn(self, conn: sqlite3.Connection) -> None:
        """Close connection unless it's the cached in-memory one."""
        if self.db_path != ":memory:":
            conn.close()

    def init_database(self):
        """Initialize SQLite database with schema"""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                owner_id TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_type TEXT,
                total_pages INTEGER DEFAULT 0,
                total_chunks INTEGER DEFAULT 0,
                cached_markdown TEXT,
                uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_sessions (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                mode TEXT NOT NULL DEFAULT 'auto',
                status TEXT NOT NULL DEFAULT 'extracting',
                error_message TEXT,
                progress_message TEXT,
                feature_drafts_json TEXT,
                questions_json TEXT,
                features_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        ''')

        # Add progress_message column if missing (migration for existing DBs)
        try:
            cursor.execute("ALTER TABLE analysis_sessions ADD COLUMN progress_message TEXT")
        except Exception:
            pass  # Column already exists

        conn.commit()
        self._close_conn(conn)

    # ── Users ──────────────────────────────────────────────

    def create_user(self, email: str, display_name: str, password_hash: str) -> Dict:
        conn = self._get_conn()
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO users (id, email, display_name, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, email, display_name, password_hash, now),
        )
        conn.commit()
        user = dict(conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())
        self._close_conn(conn)
        return user

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        self._close_conn(conn)
        return dict(row) if row else None

    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        self._close_conn(conn)
        return dict(row) if row else None

    # ── Projects ───────────────────────────────────────────

    def create_project(self, name: str, description: str, owner_id: str) -> Dict:
        conn = self._get_conn()
        project_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO projects (id, name, description, owner_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (project_id, name, description or "", owner_id, now),
        )
        conn.commit()
        project = dict(conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone())
        self._close_conn(conn)
        return project

    def get_projects_by_owner(self, owner_id: str) -> List[Dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM projects WHERE owner_id = ? ORDER BY created_at DESC", (owner_id,)
        ).fetchall()
        self._close_conn(conn)
        return [dict(r) for r in rows]

    def get_project(self, project_id: str) -> Optional[Dict]:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        self._close_conn(conn)
        return dict(row) if row else None

    def delete_project(self, project_id: str) -> bool:
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
        self._close_conn(conn)
        return cursor.rowcount > 0

    # ── Documents ──────────────────────────────────────────

    def save_document(
        self,
        doc_id: str,
        project_id: str,
        filename: str,
        file_path: str,
        file_type: str,
        total_pages: int = 0,
        total_chunks: int = 0,
        cached_markdown: str = None,
    ) -> Dict:
        conn = self._get_conn()
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """INSERT INTO documents
               (id, project_id, filename, file_path, file_type, total_pages, total_chunks, cached_markdown, uploaded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (doc_id, project_id, filename, file_path, file_type, total_pages, total_chunks, cached_markdown, now),
        )
        conn.commit()
        doc = dict(conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone())
        self._close_conn(conn)
        return doc

    def get_documents_by_project(self, project_id: str) -> List[Dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM documents WHERE project_id = ? ORDER BY uploaded_at DESC", (project_id,)
        ).fetchall()
        self._close_conn(conn)
        return [dict(r) for r in rows]

    def get_document(self, doc_id: str) -> Optional[Dict]:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
        self._close_conn(conn)
        return dict(row) if row else None

    def delete_document(self, doc_id: str) -> bool:
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
        self._close_conn(conn)
        return cursor.rowcount > 0

    # ── Analysis Sessions ─────────────────────────────────

    def create_analysis_session(self, session_id: str, project_id: str, mode: str) -> Dict:
        conn = self._get_conn()
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """INSERT INTO analysis_sessions
               (id, project_id, mode, status, created_at, updated_at)
               VALUES (?, ?, ?, 'extracting', ?, ?)""",
            (session_id, project_id, mode, now, now),
        )
        conn.commit()
        row = dict(conn.execute("SELECT * FROM analysis_sessions WHERE id = ?", (session_id,)).fetchone())
        self._close_conn(conn)
        return row

    def update_analysis_session(self, session_id: str, **kwargs) -> None:
        if not kwargs:
            return
        conn = self._get_conn()
        kwargs["updated_at"] = datetime.now(timezone.utc).isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [session_id]
        conn.execute(f"UPDATE analysis_sessions SET {set_clause} WHERE id = ?", values)
        conn.commit()
        self._close_conn(conn)

    def get_analysis_session(self, session_id: str) -> Optional[Dict]:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM analysis_sessions WHERE id = ?", (session_id,)).fetchone()
        self._close_conn(conn)
        return dict(row) if row else None

    def get_latest_analysis_session(self, project_id: str) -> Optional[Dict]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM analysis_sessions WHERE project_id = ? ORDER BY created_at DESC LIMIT 1",
            (project_id,),
        ).fetchone()
        self._close_conn(conn)
        return dict(row) if row else None

    def get_analysis_sessions(self, project_id: str) -> List[Dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM analysis_sessions WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        ).fetchall()
        self._close_conn(conn)
        return [dict(row) for row in rows]

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from backend.infrastructure.config.settings import AppSettings
from backend.infrastructure.memory.base import BaseMemoryStore

logger = logging.getLogger(__name__)


class SQLiteMemory(BaseMemoryStore):
    """SQLite-backed conversation memory store for multi-turn chat sessions."""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database table for chat history."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_session ON chat_history (session_id)")
            conn.commit()

    def save_message(self, session_id: str, role: str, content: str) -> None:
        """Save chat message (user or assistant) to session memory."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, content),
            )
            conn.commit()

    def get_history(self, session_id: str, limit: int = 10) -> list[dict[str, str]]:
        """Retrieve recent conversation history for session."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT role, content FROM chat_history
                WHERE session_id = ?
                ORDER BY id DESC LIMIT ?
                """,
                (session_id, limit),
            )
            rows = cursor.fetchall()
            return [{"role": row[0], "content": row[1]} for row in reversed(rows)]

    def clear_session(self, session_id: str) -> None:
        """Clear all messages for a session."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_history WHERE session_id = ?", (session_id,))
            conn.commit()

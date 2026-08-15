import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.domain.exceptions import InternalError, ValidationError

logger = logging.getLogger(__name__)


class UserRepository:
    """SQLite repository managing users, profiles, content generation history and writing samples."""

    def __init__(self, db_path: str = "data/memory.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self) -> None:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Users table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                # User Profiles table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_profiles (
                        user_id TEXT PRIMARY KEY,
                        profession TEXT DEFAULT '',
                        industry TEXT DEFAULT '',
                        age INTEGER DEFAULT 30,
                        gender TEXT DEFAULT 'Male',
                        preferred_language TEXT DEFAULT 'English',
                        hobbies TEXT DEFAULT '[]',
                        bio TEXT DEFAULT '',
                        updated_at TEXT NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                    """
                )
                # Auto-migrate table columns if upgrading from old schema
                cursor.execute("PRAGMA table_info(user_profiles)")
                existing_cols = {row[1] for row in cursor.fetchall()}
                if "age" not in existing_cols:
                    cursor.execute("ALTER TABLE user_profiles ADD COLUMN age INTEGER DEFAULT 30")
                if "gender" not in existing_cols:
                    cursor.execute("ALTER TABLE user_profiles ADD COLUMN gender TEXT DEFAULT 'Male'")
                if "hobbies" not in existing_cols:
                    cursor.execute("ALTER TABLE user_profiles ADD COLUMN hobbies TEXT DEFAULT '[]'")
                if "bio" not in existing_cols:
                    cursor.execute("ALTER TABLE user_profiles ADD COLUMN bio TEXT DEFAULT ''")

                # User Content Generation History table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_content_history (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        content_type TEXT NOT NULL,
                        prompt TEXT NOT NULL,
                        image_path TEXT DEFAULT '',
                        generated_content TEXT NOT NULL,
                        plan_breakdown TEXT DEFAULT '',
                        rating INTEGER DEFAULT 0,
                        saved_to_dataset INTEGER DEFAULT 0,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                    """
                )
                # User Writing Samples table (for personal few-shot RAG)
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_writing_samples (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        content_type TEXT NOT NULL,
                        content TEXT NOT NULL,
                        tags TEXT DEFAULT '[]',
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                    """
                )
                self._seed_demo_users_if_empty(cursor)
                conn.commit()
        except Exception as exc:
            logger.error(f"Failed to initialize auth and profile tables: {exc}", exc_info=True)
            raise InternalError(f"Database table initialization failed: {exc}") from exc

    def _seed_demo_users_if_empty(self, cursor: sqlite3.Cursor) -> None:
        """Seed initial demo users if database has no accounts."""
        try:
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                from backend.infrastructure.auth.password_hasher import PasswordHasher
                demo_pw = PasswordHasher.hash_password("password123")
                now = datetime.now(timezone.utc).isoformat()
                demo_users = [
                    (
                        str(uuid.uuid4()),
                        "alex_techlead",
                        "alex@example.com",
                        demo_pw,
                        "Lead AI Architect",
                        "Enterprise AI",
                        34,
                        "Male",
                        "English",
                        json.dumps(["Generative AI", "Bouldering", "Espresso Brewing", "Clean Architecture"]),
                        "Lead AI Architect with 12+ years designing distributed systems. Writes with clear logic, dry humor, and hands-on grounding without corporate fluff.",
                    ),
                    (
                        str(uuid.uuid4()),
                        "eva_ml_engineer",
                        "eva@example.com",
                        demo_pw,
                        "Senior ML Engineer",
                        "Machine Learning & Data",
                        29,
                        "Female",
                        "English",
                        json.dumps(["LLM Agents", "Hiking", "Open Source", "Sci-Fi"]),
                        "Senior ML engineer passionate about RAG pipelines, fine-tuning, and semantic memory. Loves sharing hands-on code patterns, post-mortems, and practical benchmarks.",
                    ),
                ]
                for u_id, u_name, u_email, u_pw, prof, ind, age, gen, lang, hobs, bio in demo_users:
                    cursor.execute(
                        "INSERT INTO users (id, username, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                        (u_id, u_name, u_email, u_pw, now),
                    )
                    cursor.execute(
                        """
                        INSERT INTO user_profiles (
                            user_id, profession, industry, age, gender, preferred_language,
                            hobbies, bio, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (u_id, prof, ind, age, gen, lang, hobs, bio, now),
                    )
        except Exception as exc:
            logger.warning(f"Could not seed demo users: {exc}")

    def list_all_users(self, limit: int = 50) -> list[dict[str, Any]]:
        """List registered users with profiles for quick dev selection."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT u.id, u.username, u.email, u.created_at,
                       COALESCE(p.profession, '') as profession,
                       COALESCE(p.industry, '') as industry,
                       COALESCE(p.gender, '') as gender,
                       COALESCE(p.age, 30) as age
                FROM users u
                LEFT JOIN user_profiles p ON u.id = p.user_id
                ORDER BY u.created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def create_user(
        self, username: str, email: str, password_hash: str
    ) -> dict[str, Any]:
        """Create new user and initialize empty profile."""
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (id, username, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                    (user_id, username.strip(), email.strip().lower(), password_hash, now),
                )
                # Initialize default profile
                cursor.execute(
                    """
                    INSERT INTO user_profiles (
                        user_id, profession, industry, age, gender, preferred_language,
                        hobbies, bio, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        "Software Engineer",
                        "Technology",
                        30,
                        "Male",
                        "English",
                        json.dumps(["AI", "Software Architecture", "Coffee"]),
                        "Software engineer and tech enthusiast. I enjoy building clean systems, experimenting with LLMs, and sharing practical takeaways.",
                        now,
                    ),
                )
                conn.commit()
                return {
                    "id": user_id,
                    "username": username.strip(),
                    "email": email.strip().lower(),
                    "created_at": now,
                }
        except sqlite3.IntegrityError as exc:
            err_msg = str(exc).lower()
            if "username" in err_msg:
                raise ValidationError("Username is already taken") from exc
            elif "email" in err_msg:
                raise ValidationError("Email is already registered") from exc
            else:
                raise ValidationError("User already exists") from exc
        except Exception as exc:
            logger.error(f"Error creating user: {exc}", exc_info=True)
            raise InternalError(f"Failed to create user: {exc}") from exc

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        """Fetch user by email."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        """Fetch user by username."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username.strip(),))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        """Fetch user by id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, email, created_at FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_profile(self, user_id: str) -> dict[str, Any] | None:
        """Fetch full user profile."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT u.id as user_id, u.username, u.email,
                       p.profession, p.industry, p.age, p.gender, p.preferred_language,
                       p.hobbies, p.bio, p.updated_at
                FROM users u
                LEFT JOIN user_profiles p ON u.id = p.user_id
                WHERE u.id = ?
                """,
                (user_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            res = dict(row)
            try:
                res["hobbies"] = json.loads(res.get("hobbies") or "[]")
            except Exception:
                res["hobbies"] = []
            if res.get("age") is None:
                res["age"] = 30
            if not res.get("gender"):
                res["gender"] = "Male"
            return res

    def update_user_profile(self, user_id: str, profile_data: dict[str, Any]) -> dict[str, Any]:
        """Update user profile fields."""
        now = datetime.now(timezone.utc).isoformat()
        hobbies_list = profile_data.get("hobbies") or profile_data.get("interests") or []
        hobbies_json = json.dumps(hobbies_list if isinstance(hobbies_list, list) else [str(hobbies_list)])
        bio_text = profile_data.get("bio") or profile_data.get("style_notes") or ""

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_profiles (
                    user_id, profession, industry, age, gender, preferred_language,
                    hobbies, bio, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    profession=excluded.profession,
                    industry=excluded.industry,
                    age=excluded.age,
                    gender=excluded.gender,
                    preferred_language=excluded.preferred_language,
                    hobbies=excluded.hobbies,
                    bio=excluded.bio,
                    updated_at=excluded.updated_at
                """,
                (
                    user_id,
                    profile_data.get("profession", ""),
                    profile_data.get("industry", ""),
                    int(profile_data.get("age") or 30),
                    profile_data.get("gender", "Male"),
                    profile_data.get("preferred_language", "English"),
                    hobbies_json,
                    bio_text,
                    now,
                ),
            )
            conn.commit()

        updated = self.get_user_profile(user_id)
        if not updated:
            raise InternalError("Failed to retrieve updated profile")
        return updated

    def save_content_history(
        self,
        user_id: str,
        content_type: str,
        prompt: str,
        generated_content: str,
        plan_breakdown: str = "",
        image_path: str = "",
    ) -> dict[str, Any]:
        """Save a generated content piece into user history."""
        history_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_content_history (
                    id, user_id, content_type, prompt, image_path,
                    generated_content, plan_breakdown, rating, saved_to_dataset, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, ?)
                """,
                (
                    history_id,
                    user_id,
                    content_type,
                    prompt,
                    image_path,
                    generated_content,
                    plan_breakdown,
                    now,
                ),
            )
            conn.commit()
        return {
            "id": history_id,
            "user_id": user_id,
            "content_type": content_type,
            "prompt": prompt,
            "image_path": image_path,
            "generated_content": generated_content,
            "plan_breakdown": plan_breakdown,
            "rating": 0,
            "saved_to_dataset": False,
            "created_at": now,
        }

    def get_content_history(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent content generations for a user."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, user_id, content_type, prompt, image_path,
                       generated_content, plan_breakdown, rating, saved_to_dataset, created_at
                FROM user_content_history
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
            rows = cursor.fetchall()
            return [
                {
                    **dict(row),
                    "saved_to_dataset": bool(row["saved_to_dataset"]),
                }
                for row in rows
            ]

    def update_content_feedback(
        self, history_id: str, user_id: str, rating: int, save_to_dataset: bool
    ) -> dict[str, Any]:
        """Update rating and dataset flag for a content generation."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE user_content_history
                SET rating = ?, saved_to_dataset = ?
                WHERE id = ? AND user_id = ?
                """,
                (rating, 1 if save_to_dataset else 0, history_id, user_id),
            )
            conn.commit()
            cursor.execute(
                "SELECT * FROM user_content_history WHERE id = ? AND user_id = ?",
                (history_id, user_id),
            )
            row = cursor.fetchone()
            if not row:
                raise ValidationError("Content history item not found")
            return {
                **dict(row),
                "saved_to_dataset": bool(row["saved_to_dataset"]),
            }

    def save_writing_sample(
        self,
        user_id: str,
        title: str,
        content_type: str,
        content: str,
        tags: list[str] | None = None,
        sample_id: str | None = None,
    ) -> dict[str, Any]:
        """Save a new writing sample into user_writing_samples."""
        s_id = sample_id or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        tags_json = json.dumps(tags or [])
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_writing_samples (id, user_id, title, content_type, content, tags, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (s_id, user_id, title.strip(), content_type, content.strip(), tags_json, now),
            )
            conn.commit()
        return {
            "id": s_id,
            "user_id": user_id,
            "title": title.strip(),
            "content_type": content_type,
            "content": content.strip(),
            "tags": tags or [],
            "created_at": now,
        }

    def list_writing_samples(self, user_id: str) -> list[dict[str, Any]]:
        """List all few-shot writing samples from user_writing_samples table."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, user_id, title, content_type, content, tags, created_at
                FROM user_writing_samples
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
            results = []
            for row in rows:
                item = dict(row)
                try:
                    item["tags"] = json.loads(item.get("tags") or "[]")
                except Exception:
                    item["tags"] = [item["content_type"]]
                results.append(item)
            return results

    def delete_writing_sample(self, sample_id: str, user_id: str) -> bool:
        """Delete sample from user_writing_samples."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM user_writing_samples WHERE id = ? AND user_id = ?",
                (sample_id, user_id),
            )
            conn.commit()
            return cursor.rowcount > 0

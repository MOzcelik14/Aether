import os
import shutil
import sqlite3
from pathlib import Path


APP_DIR_NAME = "aether"
LEGACY_DIR_NAME = "local-ai"


def _data_home() -> Path:
    value = os.environ.get("XDG_DATA_HOME")
    if value:
        return Path(value).expanduser()
    return Path.home() / ".local" / "share"


class Database:
    def __init__(self):
        data_dir = _data_home() / APP_DIR_NAME
        data_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = data_dir / "history.db"
        self.legacy_db_path = (
            Path.home()
            / ".local"
            / "share"
            / LEGACY_DIR_NAME
            / "history.db"
        )

        self._migrate_legacy_database()

        self.conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
        )

        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA busy_timeout = 5000")
        self.conn.execute("PRAGMA journal_mode = WAL")

        self.create_tables()
        self._migrate_schema()

    def _migrate_legacy_database(self):
        if self.db_path.exists() or not self.legacy_db_path.exists():
            return

        try:
            shutil.copy2(self.legacy_db_path, self.db_path)
        except OSError as error:
            print(f"Sohbet geçmişi taşınamadı: {error}")

    def create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(chat_id)
                    REFERENCES chats(id)
                    ON DELETE CASCADE
            )
        """)

        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_chat_id
            ON messages(chat_id)
        """)

        self.conn.commit()

    def _columns(self, table):
        cursor = self.conn.execute(f"PRAGMA table_info({table})")
        return {row[1] for row in cursor.fetchall()}

    def _migrate_schema(self):
        chat_columns = self._columns("chats")
        message_columns = self._columns("messages")

        if "updated_at" not in chat_columns:
            self.conn.execute(
                "ALTER TABLE chats ADD COLUMN updated_at TIMESTAMP"
            )
            self.conn.execute(
                "UPDATE chats SET updated_at = COALESCE(created_at, CURRENT_TIMESTAMP)"
            )

        if "created_at" not in message_columns:
            self.conn.execute(
                "ALTER TABLE messages ADD COLUMN created_at TIMESTAMP"
            )
            self.conn.execute(
                "UPDATE messages SET created_at = CURRENT_TIMESTAMP "
                "WHERE created_at IS NULL"
            )

        self.conn.commit()

    def create_chat(self, title="Yeni sohbet"):
        cursor = self.conn.execute(
            "INSERT INTO chats (title) VALUES (?)",
            (title,),
        )
        self.conn.commit()
        return cursor.lastrowid

    def add_message(self, chat_id, role, content):
        self.conn.execute(
            """
            INSERT INTO messages (chat_id, role, content)
            VALUES (?, ?, ?)
            """,
            (chat_id, role, content),
        )
        self._touch_chat(chat_id)
        self.conn.commit()

    def _touch_chat(self, chat_id):
        self.conn.execute(
            """
            UPDATE chats
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (chat_id,),
        )

    def update_chat_title(self, chat_id, title):
        self.conn.execute(
            """
            UPDATE chats
            SET title = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (title, chat_id),
        )
        self.conn.commit()

    def get_chats(self):
        cursor = self.conn.execute("""
            SELECT id, title
            FROM chats
            ORDER BY updated_at DESC, id DESC
        """)
        return cursor.fetchall()

    def get_messages(self, chat_id):
        cursor = self.conn.execute(
            """
            SELECT role, content
            FROM messages
            WHERE chat_id = ?
            ORDER BY id ASC
            """,
            (chat_id,),
        )
        return cursor.fetchall()

    def search_chat_ids(self, query):
        query = (query or "").strip()
        if not query:
            return {chat_id for chat_id, _ in self.get_chats()}

        needle = f"%{query}%"

        cursor = self.conn.execute(
            """
            SELECT DISTINCT chats.id
            FROM chats
            LEFT JOIN messages ON messages.chat_id = chats.id
            WHERE chats.title LIKE ? COLLATE NOCASE
               OR messages.content LIKE ? COLLATE NOCASE
            """,
            (needle, needle),
        )

        return {row[0] for row in cursor.fetchall()}

    def delete_last_message(self, chat_id, role=None):
        if role is None:
            cursor = self.conn.execute(
                """
                SELECT id
                FROM messages
                WHERE chat_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (chat_id,),
            )
        else:
            cursor = self.conn.execute(
                """
                SELECT id
                FROM messages
                WHERE chat_id = ? AND role = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (chat_id, role),
            )

        row = cursor.fetchone()
        if row is None:
            return False

        self.conn.execute(
            "DELETE FROM messages WHERE id = ?",
            (row[0],),
        )
        self._touch_chat(chat_id)
        self.conn.commit()
        return True

    def delete_chat(self, chat_id):
        # Keep the explicit message delete for databases created by Aether 1.0,
        # whose foreign key did not include ON DELETE CASCADE.
        self.conn.execute(
            "DELETE FROM messages WHERE chat_id = ?",
            (chat_id,),
        )
        self.conn.execute(
            "DELETE FROM chats WHERE id = ?",
            (chat_id,),
        )
        self.conn.commit()

    def close(self):
        if getattr(self, "conn", None) is not None:
            self.conn.close()
            self.conn = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

import sqlite3
from pathlib import Path


class Database:
    def __init__(self):
        data_dir = Path.home() / ".local" / "share" / "local-ai"
        data_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = data_dir / "history.db"

        self.conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False
        )

        self.create_tables()

    def create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                FOREIGN KEY(chat_id) REFERENCES chats(id)
            )
        """)

        self.conn.commit()

    def create_chat(self, title="Yeni sohbet"):
        cursor = self.conn.execute(
            "INSERT INTO chats (title) VALUES (?)",
            (title,)
        )

        self.conn.commit()
        return cursor.lastrowid

    def add_message(self, chat_id, role, content):
        self.conn.execute(
            """
            INSERT INTO messages
            (chat_id, role, content)
            VALUES (?, ?, ?)
            """,
            (chat_id, role, content)
        )

        self.conn.commit()

    def update_chat_title(self, chat_id, title):
        self.conn.execute(
            "UPDATE chats SET title = ? WHERE id = ?",
            (title, chat_id)
        )

        self.conn.commit()

    def get_chats(self):
        cursor = self.conn.execute("""
            SELECT id, title
            FROM chats
            ORDER BY id DESC
        """)

        return cursor.fetchall()

    def get_messages(self, chat_id):
        cursor = self.conn.execute("""
            SELECT role, content
            FROM messages
            WHERE chat_id = ?
            ORDER BY id ASC
        """, (chat_id,))

        return cursor.fetchall()

    def delete_chat(self, chat_id):
        self.conn.execute(
            "DELETE FROM messages WHERE chat_id = ?",
            (chat_id,)
        )

        self.conn.execute(
            "DELETE FROM chats WHERE id = ?",
            (chat_id,)
        )

        self.conn.commit()

    def close(self):
        self.conn.close()

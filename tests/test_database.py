import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from database import Database


class DatabaseTests(unittest.TestCase):
    def test_chat_lifecycle_and_content_search(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)

            with patch.dict(
                os.environ,
                {
                    "HOME": str(home),
                    "XDG_DATA_HOME": str(home / "data"),
                },
                clear=False,
            ):
                database = Database()
                chat_id = database.create_chat("Linux")

                database.add_message(
                    chat_id,
                    "user",
                    "Debian üzerinde Ollama nasıl çalışır?",
                )
                database.add_message(
                    chat_id,
                    "assistant",
                    "Yerel servis üzerinden çalışabilir.",
                )

                self.assertIn(
                    chat_id,
                    database.search_chat_ids("Ollama"),
                )
                self.assertTrue(
                    database.delete_last_message(
                        chat_id,
                        "assistant",
                    )
                )
                self.assertEqual(
                    database.get_messages(chat_id),
                    [
                        (
                            "user",
                            "Debian üzerinde Ollama nasıl çalışır?",
                        )
                    ],
                )

                database.delete_chat(chat_id)
                self.assertEqual(database.get_chats(), [])
                database.close()


if __name__ == "__main__":
    unittest.main()

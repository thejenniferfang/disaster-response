"""
MongoDB init helper.

Run:
  python mongo_init.py

What it does:
  - Connects to MongoDB
  - Ensures indexes exist for the pipeline collections
  - Pings the server to confirm connectivity
"""

from src.database import get_database
from src.database.connection import get_client, close_connection
from src.database.pipeline_mongo import ensure_pipeline_indexes


def main() -> None:
    print("Initializing MongoDB collections + indexes...")

    # Force connection + ping
    client = get_client()
    client.admin.command("ping")

    # Force DB handle creation (helps catch auth/db-name issues early)
    db = get_database()
    print(f"Connected to database: {db.name}")

    ensure_pipeline_indexes()

    print("MongoDB init complete (indexes ensured).")


if __name__ == "__main__":
    try:
        main()
    finally:
        close_connection()


"""Database initialization script.

This script creates all database tables defined in the models.
For production use, consider using Alembic for migrations.
"""

import asyncio
import os

from vtt_transcribe.api.database import init_db


async def main() -> None:
    """Initialize database tables."""
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./vtt_transcribe.db")
    print(f"Initializing database at: {database_url}")

    await init_db()

    print("Database initialized successfully!")
    print("\nDefault tables created:")
    print("  - users (user accounts)")
    print("  - api_keys (encrypted service API keys)")
    print("  - transcription_jobs (job history and transcripts)")


if __name__ == "__main__":
    asyncio.run(main())

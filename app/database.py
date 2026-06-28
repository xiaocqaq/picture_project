import aiosqlite
from pathlib import Path
from app.config import settings

DB_PATH = settings.DB_PATH
IMAGES_DIR = settings.IMAGES_DIR

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    prompt TEXT NOT NULL,
    size TEXT NOT NULL,
    quality TEXT NOT NULL,
    image_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_history_user ON history(user_id, created_at DESC);
"""


async def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(IMAGES_DIR).mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()


def get_db():
    return aiosqlite.connect(DB_PATH)

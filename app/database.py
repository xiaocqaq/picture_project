import aiosqlite
from pathlib import Path
from app.config import settings

DB_PATH = settings.DB_PATH
IMAGES_DIR = settings.IMAGES_DIR
THUMBS_DIR = str(Path(IMAGES_DIR) / "thumbs")

THUMBS_DIR = str(Path(IMAGES_DIR) / "thumbs")

SCHEMA = """
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt TEXT NOT NULL,
    size TEXT NOT NULL,
    quality TEXT NOT NULL,
    image_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


async def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(IMAGES_DIR).mkdir(parents=True, exist_ok=True)
    Path(THUMBS_DIR).mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()


def get_db():
    return aiosqlite.connect(DB_PATH)

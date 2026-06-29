import base64
import logging
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.database import init_db, get_db, IMAGES_DIR, THUMBS_DIR
from app.service import generate_image, AVAILABLE_SIZES, AVAILABLE_QUALITIES

logger = logging.getLogger("app")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = FastAPI(title="AI Image Generator")

STATIC_DIR = Path(__file__).parent / "static"
THUMB_MAX_SIZE = (400, 400)


def create_thumbnail(src_path: Path, filename: str) -> bool:
    try:
        from PIL import Image, ImageOps

        thumb_path = Path(THUMBS_DIR) / filename
        thumb_path.parent.mkdir(parents=True, exist_ok=True)

        with Image.open(src_path) as image:
            image = ImageOps.exif_transpose(image)
            image.thumbnail(THUMB_MAX_SIZE, Image.Resampling.LANCZOS)
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
            image.save(thumb_path, "PNG", optimize=True)
        return True
    except Exception:
        logger.warning("Thumbnail creation failed for %s", src_path, exc_info=True)
        return False


def _history_item(row: tuple) -> dict:
    filename = row[4]
    return {
        "id": row[0],
        "prompt": row[1],
        "size": row[2],
        "quality": row[3],
        "image_path": filename,
        "image_url": f"images/{filename}",
        "thumb_url": f"thumbs/{filename}",
        "created_at": row[5],
    }


@app.on_event("startup")
async def startup():
    await init_db()


class GenerateRequest(BaseModel):
    prompt: str
    size: str = "1024x1024"
    quality: str = "medium"
    n: int = 1


class GenerateResponse(BaseModel):
    images: list[dict]
    prompt: str
    size: str
    quality: str


@app.post("/api/generate", response_model=GenerateResponse)
async def api_generate(req: GenerateRequest):
    if req.size not in AVAILABLE_SIZES:
        raise HTTPException(400, f"size must be one of {AVAILABLE_SIZES}")
    if req.quality not in AVAILABLE_QUALITIES:
        raise HTTPException(400, f"quality must be one of {AVAILABLE_QUALITIES}")
    if not req.prompt.strip():
        raise HTTPException(400, "prompt cannot be empty")
    if req.n < 1 or req.n > 4:
        raise HTTPException(400, "n must be between 1 and 4")

    logger.info("Generating image: prompt=%r, size=%s, quality=%s, n=%d", req.prompt[:80], req.size, req.quality, req.n)
    start = time.time()

    try:
        images = await generate_image(
            prompt=req.prompt.strip(),
            size=req.size,
            quality=req.quality,
            n=req.n,
        )
    except Exception as e:
        logger.error("Generation failed after %.1fs: %s", time.time() - start, e)
        raise HTTPException(502, f"Image generation failed: {e}")

    elapsed = time.time() - start
    logger.info("Generation done: %d image(s) in %.1fs", len(images), elapsed)

    async with get_db() as db:
        for img in images:
            filename = f"{uuid.uuid4().hex}.png"
            filepath = Path(IMAGES_DIR) / filename
            img_bytes = base64.b64decode(img["b64_json"])
            filepath.write_bytes(img_bytes)
            try:
                create_thumbnail(filepath, filename)
            except Exception:
                logger.warning("Unexpected thumbnail failure for %s", filepath, exc_info=True)
            await db.execute(
                "INSERT INTO history (prompt, size, quality, image_path) VALUES (?, ?, ?, ?)",
                (req.prompt.strip(), req.size, req.quality, filename),
            )
            img["filename"] = filename
        await db.commit()

    return GenerateResponse(
        images=images,
        prompt=req.prompt.strip(),
        size=req.size,
        quality=req.quality,
    )


@app.get("/api/history")
async def api_history(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    offset = (page - 1) * page_size
    async with get_db() as db:
        db.row_factory = None
        cursor = await db.execute("SELECT COUNT(*) FROM history")
        total = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT id, prompt, size, quality, image_path, created_at FROM history ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (page_size, offset),
        )
        rows = await cursor.fetchall()

    items = [_history_item(r) for r in rows]
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@app.delete("/api/history/{record_id}")
async def api_delete_history(record_id: int):
    async with get_db() as db:
        cursor = await db.execute("SELECT image_path FROM history WHERE id = ?", (record_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(404, "Record not found")

        filepath = Path(IMAGES_DIR) / row[0]
        if filepath.exists():
            filepath.unlink()

        thumb_path = Path(THUMBS_DIR) / row[0]
        if thumb_path.exists():
            thumb_path.unlink()

        await db.execute("DELETE FROM history WHERE id = ?", (record_id,))
        await db.commit()
    return {"ok": True}


@app.get("/api/options")
async def api_options():
    return {"sizes": AVAILABLE_SIZES, "qualities": AVAILABLE_QUALITIES}


@app.get("/images/{filename}")
async def serve_image(filename: str):
    filepath = Path(IMAGES_DIR) / filename
    if not filepath.exists():
        raise HTTPException(404, "Image not found")
    return FileResponse(filepath, media_type="image/png")


@app.get("/thumbs/{filename}")
async def serve_thumb(filename: str):
    thumb_path = Path(THUMBS_DIR) / filename
    original_path = Path(IMAGES_DIR) / filename
    if not original_path.exists():
        raise HTTPException(404, "Image not found")

    if not thumb_path.exists():
        try:
            create_thumbnail(original_path, filename)
        except Exception:
            logger.warning("Unexpected thumbnail failure for %s", original_path, exc_info=True)

    if thumb_path.exists():
        return FileResponse(thumb_path, media_type="image/png")
    return FileResponse(original_path, media_type="image/png")


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

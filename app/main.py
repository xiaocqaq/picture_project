import logging
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.service import generate_image, AVAILABLE_SIZES, AVAILABLE_QUALITIES

logger = logging.getLogger("app")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = FastAPI(title="NayutoAI Image Generator")

STATIC_DIR = Path(__file__).parent / "static"


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

    return GenerateResponse(
        images=images,
        prompt=req.prompt.strip(),
        size=req.size,
        quality=req.quality,
    )


@app.get("/api/options")
async def api_options():
    return {"sizes": AVAILABLE_SIZES, "qualities": AVAILABLE_QUALITIES}


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

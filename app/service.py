import base64
import logging
import os

import httpx
from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger("app")


_client = AsyncOpenAI(
    api_key=settings.NAYUTO_API_KEY,
    base_url=settings.NAYUTO_BASE_URL,
    timeout=360.0,
    max_retries=0,
)


def describe_client() -> dict:
    timeout = _client.timeout
    return {
        "base_url": str(_client.base_url),
        "timeout": {
            "connect": getattr(timeout, "connect", None),
            "read": getattr(timeout, "read", None),
            "write": getattr(timeout, "write", None),
            "pool": getattr(timeout, "pool", None),
        },
        "max_retries": _client.max_retries,
        "proxy_env": {
            name: "SET" if os.environ.get(name) else "UNSET"
            for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY")
        },
    }


def format_exception_chain(exc: BaseException) -> str:
    parts = []
    current: BaseException | None = exc
    seen = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        parts.append(f"{type(current).__name__}: {current!s}")
        current = current.__cause__ or current.__context__
    return " <- ".join(parts)

AVAILABLE_SIZES = ["1024x1024", "1024x1536", "1536x1024"]
AVAILABLE_QUALITIES = ["low", "medium", "high"]


async def generate_image(
    prompt: str,
    size: str = "1024x1024",
    quality: str = "medium",
    n: int = 1,
) -> list[dict]:
    logger.info("Image client config: %r", describe_client())
    response = await _client.images.generate(
        model="gpt-image-2",
        prompt=prompt,
        n=n,
        size=size,
        quality=quality,
        response_format="b64_json",
    )

    results = []
    for item in response.data:
        img_b64 = item.b64_json
        results.append({
            "b64_json": img_b64,
            "data_url": f"data:image/png;base64,{img_b64}",
        })
    return results

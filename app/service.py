import base64
from openai import AsyncOpenAI
from app.config import settings


_client = AsyncOpenAI(
    api_key=settings.NAYUTO_API_KEY,
    base_url=settings.NAYUTO_BASE_URL,
)

AVAILABLE_SIZES = ["1024x1024", "1024x1536", "1536x1024"]
AVAILABLE_QUALITIES = ["low", "medium", "high"]


async def generate_image(
    prompt: str,
    size: str = "1024x1024",
    quality: str = "medium",
    n: int = 1,
) -> list[dict]:
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

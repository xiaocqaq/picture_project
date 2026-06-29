import base64
import importlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from PIL import Image


PNG_1X1 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    "/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


class ThumbnailHistoryTest(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("NAYUTO_API_KEY", "test-key")

    def test_create_thumbnail_writes_small_image(self):
        main = importlib.import_module("app.main")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.png"
            thumbs = root / "thumbs"
            thumbs.mkdir()

            image = Image.new("RGB", (900, 600), color=(10, 20, 30))
            image.save(source, "PNG")

            with patch.object(main, "THUMBS_DIR", str(thumbs)):
                self.assertTrue(main.create_thumbnail(source, "source.png"))

            thumb_path = thumbs / "source.png"
            self.assertTrue(thumb_path.exists())
            with Image.open(thumb_path) as thumb:
                self.assertLessEqual(max(thumb.size), 400)

    def test_generate_succeeds_when_thumbnail_creation_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / "app.db"
            images_dir = root / "images"
            thumbs_dir = root / "thumbs"

            with patch.dict(
                os.environ,
                {
                    "NAYUTO_API_KEY": "test-key",
                    "DB_PATH": str(db_path),
                    "IMAGES_DIR": str(images_dir),
                    "THUMBS_DIR": str(thumbs_dir),
                },
            ):
                import app.config as config
                import app.database as database
                import app.main as main

                importlib.reload(config)
                importlib.reload(database)
                main = importlib.reload(main)

                generated = [{
                    "b64_json": PNG_1X1,
                    "data_url": f"data:image/png;base64,{PNG_1X1}",
                }]

                with patch.object(main, "generate_image", new=AsyncMock(return_value=generated)):
                    with patch.object(main, "create_thumbnail", side_effect=RuntimeError("boom")):
                        with TestClient(main.app) as client:
                            response = client.post(
                                "/api/generate",
                                json={"prompt": "test", "size": "1024x1024", "quality": "medium", "n": 1},
                            )
                            self.assertEqual(200, response.status_code)
                            self.assertEqual(1, len(response.json()["images"]))

                            history = client.get("/api/history?page=1&page_size=12")
                            self.assertEqual(200, history.status_code)
                            item = history.json()["items"][0]
                            self.assertIn("thumb_url", item)
                            self.assertIn("image_url", item)

                            thumb = client.get(item["thumb_url"])
                            self.assertEqual(200, thumb.status_code)

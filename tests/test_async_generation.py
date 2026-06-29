import importlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


PNG_1X1 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    "/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


class SynchronousGenerationTest(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("NAYUTO_API_KEY", "test-key")

    def _reload_app(self, root: Path):
        with patch.dict(
            os.environ,
            {
                "NAYUTO_API_KEY": "test-key",
                "DB_PATH": str(root / "app.db"),
                "IMAGES_DIR": str(root / "images"),
                "THUMBS_DIR": str(root / "thumbs"),
            },
        ):
            import app.config as config
            import app.database as database
            import app.main as main

            importlib.reload(config)
            importlib.reload(database)
            return importlib.reload(main)

    def test_generate_returns_images_synchronously_without_task_polling(self):
        generated = [{
            "b64_json": PNG_1X1,
            "data_url": f"data:image/png;base64,{PNG_1X1}",
        }]

        with tempfile.TemporaryDirectory() as tmp:
            main = self._reload_app(Path(tmp))
            generate_mock = AsyncMock(return_value=generated)
            with patch.object(main, "generate_image", new=generate_mock):
                with TestClient(main.app) as client:
                    response = client.post(
                        "/api/generate",
                        json={"prompt": "test", "size": "1024x1024", "quality": "medium", "n": 1},
                    )
                    self.assertEqual(200, response.status_code)
                    generate_mock.assert_awaited_once()

                    payload = response.json()
                    self.assertNotIn("task_id", payload)
                    self.assertNotIn("status", payload)
                    self.assertNotIn("progress", payload)
                    self.assertEqual("test", payload["prompt"])
                    self.assertEqual(1, len(payload["images"]))
                    image = payload["images"][0]
                    self.assertEqual(f"data:image/png;base64,{PNG_1X1}", image["data_url"])
                    self.assertRegex(image["filename"], r"^[0-9a-f]{32}\.png$")
                    self.assertEqual(f"images/{image['filename']}", image["image_url"])
                    self.assertEqual(f"thumbs/{image['filename']}", image["thumb_url"])

                    task = client.get("/api/tasks/123")
                    self.assertEqual(404, task.status_code)

    def test_thumbnail_failure_does_not_prevent_history_save(self):
        generated = [{
            "b64_json": PNG_1X1,
            "data_url": f"data:image/png;base64,{PNG_1X1}",
        }]

        with tempfile.TemporaryDirectory() as tmp:
            main = self._reload_app(Path(tmp))
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
                        self.assertEqual(1, history.json()["total"])

    def test_generate_returns_bad_gateway_when_image_generation_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = self._reload_app(Path(tmp))
            with patch.object(main, "generate_image", new=AsyncMock(side_effect=RuntimeError("api down"))):
                with TestClient(main.app) as client:
                    response = client.post(
                        "/api/generate",
                        json={"prompt": "test", "size": "1024x1024", "quality": "medium", "n": 1},
                    )
                    self.assertEqual(502, response.status_code)
                    self.assertIn("api down", response.json()["detail"])

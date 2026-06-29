import asyncio
import base64
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


class AsyncGenerationTest(unittest.TestCase):
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
            import app.tasks as tasks

            importlib.reload(config)
            importlib.reload(database)
            importlib.reload(tasks)
            return importlib.reload(main)

    def test_generate_returns_snowflake_task_id_and_task_can_be_polled(self):
        async def fake_generate_image(**_kwargs):
            await asyncio.sleep(0.01)
            return [{
                "b64_json": PNG_1X1,
                "data_url": f"data:image/png;base64,{PNG_1X1}",
            }]

        with tempfile.TemporaryDirectory() as tmp:
            main = self._reload_app(Path(tmp))
            with patch.object(main, "generate_image", side_effect=fake_generate_image):
                with TestClient(main.app) as client:
                    created = client.post(
                        "/api/generate",
                        json={"prompt": "test", "size": "1024x1024", "quality": "medium", "n": 1},
                    )
                    self.assertEqual(202, created.status_code)
                    payload = created.json()
                    self.assertRegex(payload["task_id"], r"^\d{15,}$")
                    self.assertIn(payload["status"], {"queued", "running"})

                    final = None
                    for _ in range(20):
                        polled = client.get(f"/api/tasks/{payload['task_id']}")
                        self.assertEqual(200, polled.status_code)
                        final = polled.json()
                        if final["status"] == "succeeded":
                            break
                        import time

                        time.sleep(0.05)

                    self.assertEqual("succeeded", final["status"])
                    self.assertEqual(100, final["progress"])
                    self.assertEqual(1, len(final["images"]))
                    self.assertIn("filename", final["images"][0])

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
                        created = client.post(
                            "/api/generate",
                            json={"prompt": "test", "size": "1024x1024", "quality": "medium", "n": 1},
                        )
                        self.assertEqual(202, created.status_code)
                        task_id = created.json()["task_id"]

                        final = None
                        for _ in range(20):
                            polled = client.get(f"/api/tasks/{task_id}")
                            self.assertEqual(200, polled.status_code)
                            final = polled.json()
                            if final["status"] == "succeeded":
                                break
                            import time

                            time.sleep(0.05)

                        self.assertEqual("succeeded", final["status"])
                        history = client.get("/api/history?page=1&page_size=12")
                        self.assertEqual(200, history.status_code)
                        self.assertEqual(1, history.json()["total"])

    def test_task_reports_failed_when_image_generation_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = self._reload_app(Path(tmp))
            with patch.object(main, "generate_image", new=AsyncMock(side_effect=RuntimeError("api down"))):
                with TestClient(main.app) as client:
                    created = client.post(
                        "/api/generate",
                        json={"prompt": "test", "size": "1024x1024", "quality": "medium", "n": 1},
                    )
                    self.assertEqual(202, created.status_code)
                    task_id = created.json()["task_id"]

                    final = None
                    for _ in range(20):
                        polled = client.get(f"/api/tasks/{task_id}")
                        self.assertEqual(200, polled.status_code)
                        final = polled.json()
                        if final["status"] == "failed":
                            break
                        import time

                        time.sleep(0.05)

                    self.assertEqual("failed", final["status"])
                    self.assertIn("api down", final["error"])

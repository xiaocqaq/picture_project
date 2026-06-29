from pathlib import Path
import unittest


INDEX_HTML = Path(__file__).resolve().parents[1] / "app" / "static" / "index.html"


class FrontendTaskStatusTest(unittest.TestCase):
    def test_frontend_does_not_poll_task_status_or_render_progress_percent(self):
        html = INDEX_HTML.read_text(encoding="utf-8")

        self.assertNotIn("api/tasks", html)
        self.assertNotIn("pollTask", html)
        self.assertNotIn("activeTaskId", html)
        self.assertNotIn("task.progress", html)
        self.assertNotIn("id=\"statusText\"", html)
        self.assertNotIn("const statusText", html)
        self.assertNotIn("status-bar", html)
        self.assertIn("timerEl.textContent", html)

    def test_history_lightbox_shows_prompt_and_download_button(self):
        html = INDEX_HTML.read_text(encoding="utf-8")

        self.assertIn('id="lightboxPrompt"', html)
        self.assertIn('id="lightboxDownload"', html)
        self.assertIn("function openHistoryItem", html)
        self.assertIn("data-prompt", html)
        self.assertIn("downloadUrl", html)
        self.assertIn("下载图片", html)

    def test_lightbox_download_uses_loaded_preview_blob(self):
        html = INDEX_HTML.read_text(encoding="utf-8")

        self.assertIn("function useLoadedPreviewForDownload", html)
        self.assertIn("document.createElement('canvas')", html)
        self.assertIn("canvas.toBlob", html)
        self.assertIn("URL.createObjectURL(blob)", html)
        self.assertIn("URL.revokeObjectURL", html)
        self.assertIn("lightboxImg.addEventListener('load'", html)

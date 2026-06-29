from pathlib import Path
import unittest


INDEX_HTML = Path(__file__).resolve().parents[1] / "app" / "static" / "index.html"


class FrontendTaskStatusTest(unittest.TestCase):
    def test_task_status_does_not_render_progress_percent(self):
        html = INDEX_HTML.read_text(encoding="utf-8")

        self.assertNotIn("task.progress", html)
        self.assertNotIn("id=\"statusText\"", html)
        self.assertNotIn("const statusText", html)
        self.assertNotIn("status-bar", html)
        self.assertIn("timerEl.textContent", html)

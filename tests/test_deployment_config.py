from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DeploymentConfigTest(unittest.TestCase):
    def test_aipic_defaults_to_single_worker_for_in_memory_tasks(self):
        script = (ROOT / "aipic.sh").read_text(encoding="utf-8")

        self.assertIn('WORKERS="${WORKERS:-1}"', script)

    def test_docker_uses_single_worker_for_in_memory_tasks(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn('"--workers", "1"', dockerfile)

    def test_readme_uses_single_worker_for_in_memory_tasks(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("--workers 1", readme)
        self.assertNotIn("--workers 4", readme)

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DeploymentConfigTest(unittest.TestCase):
    def test_aipic_defaults_to_single_worker_for_in_memory_tasks(self):
        script = (ROOT / "aipic.sh").read_text(encoding="utf-8")

        self.assertIn('WORKERS="${WORKERS:-1}"', script)

    def test_aipic_loads_env_and_prepares_runtime_dependencies(self):
        script = (ROOT / "aipic.sh").read_text(encoding="utf-8")

        self.assertIn("load_env()", script)
        self.assertIn("tr -d '\\r'", script)
        self.assertIn('set -a\n    . "$TMP_ENV"\n    set +a', script)
        self.assertIn('mkdir -p "$IMAGES_DIR" "$THUMBS_DIR"', script)
        self.assertIn('require_command "lsof"', script)
        self.assertIn("is_managed_process()", script)

    def test_aipic_prints_runtime_diagnostics(self):
        script = (ROOT / "aipic.sh").read_text(encoding="utf-8")

        self.assertIn("print_runtime_info()", script)
        self.assertIn("git -C \"$PROJECT_DIR\" rev-parse --short HEAD", script)
        self.assertIn("describe_client", script)

    def test_docker_uses_single_worker_for_in_memory_tasks(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn('"--workers", "1"', dockerfile)

    def test_readme_uses_single_worker_for_in_memory_tasks(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("--workers 1", readme)
        self.assertNotIn("--workers 4", readme)

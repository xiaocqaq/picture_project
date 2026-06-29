import importlib
import os
import unittest
from unittest.mock import patch


class OpenAIClientConfigTest(unittest.TestCase):
    def test_settings_strip_env_values_loaded_by_python(self):
        with patch.dict(
            os.environ,
            {
                "NAYUTO_API_KEY": " test-key\n",
                "NAYUTO_BASE_URL": "https://api.nayutoai.online/v1\r",
            },
        ):
            import app.config as config

            config = importlib.reload(config)

        self.assertEqual("test-key", config.settings.NAYUTO_API_KEY)
        self.assertEqual("https://api.nayutoai.online/v1", config.settings.NAYUTO_BASE_URL)

    def test_image_client_disables_retries_and_uses_180_second_timeout(self):
        with patch.dict(
            os.environ,
            {
                "NAYUTO_API_KEY": "test-key",
                "NAYUTO_BASE_URL": "https://api.nayutoai.online/v1",
            },
        ):
            import app.config as config
            import app.service as service

            importlib.reload(config)
            service = importlib.reload(service)

        self.assertEqual(0, service._client.max_retries)
        self.assertEqual(180.0, service._client.timeout)

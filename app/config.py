import secrets

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    NAYUTO_API_KEY: str
    NAYUTO_BASE_URL: str = "https://api.nayutoai.online/v1"
    JWT_SECRET: str = secrets.token_hex(32)
    DB_PATH: str = "data/app.db"
    IMAGES_DIR: str = "data/images"
    THUMBS_DIR: str = "data/thumbs"

    model_config = {"env_file": ".env"}

    def __init__(self, **data):
        super().__init__(**data)
        self.NAYUTO_API_KEY = self.NAYUTO_API_KEY.strip()
        self.NAYUTO_BASE_URL = self.NAYUTO_BASE_URL.strip()


settings = Settings()

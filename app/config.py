import secrets

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    NAYUTO_API_KEY: str
    NAYUTO_BASE_URL: str = "https://api.nayutoai.online/v1"
    JWT_SECRET: str = secrets.token_hex(32)
    DB_PATH: str = "data/app.db"
    IMAGES_DIR: str = "data/images"

    model_config = {"env_file": ".env"}


settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PADHOTEC_", env_file=".env")

    database_url: str = "sqlite:///./padhotec.db"
    jwt_secret: str = "dev-only-secret-change-me-before-deploying-0000"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 24
    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()

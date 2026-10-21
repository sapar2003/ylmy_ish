from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Raspisaniye API"
    database_url: str = "postgresql+psycopg://raspisaniye:raspisaniye@localhost:5432/raspisaniye"
    cors_origins: list[str] = ["*"]


settings = Settings()

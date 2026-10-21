from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Raspisaniye API"
    database_url: str = "postgresql+psycopg://raspisaniye:raspisaniye@localhost:5432/raspisaniye"
    cors_origins: list[str] = ["*"]
    generation_in_background: bool = True  # testlerde False: generasiýa şol bada gutarýar
    static_dir: str | None = None  # Flutter web build bukjasy; berilse "/" salgysyndan berilýär


settings = Settings()

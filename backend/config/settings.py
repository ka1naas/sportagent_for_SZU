from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Campus Fitness Scheduler API", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")

    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")

    llm_base_url: str = Field(default="https://api.openai.com/v1", alias="LLM_BASE_URL")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")
    llm_model_name: str = Field(default="gpt-4o-mini", alias="LLM_MODEL_NAME")

    weather_api_base_url: str = Field(
        default="https://api.openweathermap.org/data/2.5",
        alias="WEATHER_API_BASE_URL",
    )
    weather_api_key: str = Field(default="", alias="WEATHER_API_KEY")

    schedule_vlm_base_url: str = Field(
        default="https://example-vlm.local/api",
        alias="SCHEDULE_VLM_BASE_URL",
    )
    schedule_vlm_api_key: str = Field(default="", alias="SCHEDULE_VLM_API_KEY")

    data_dir: str = Field(default="backend/data", alias="DATA_DIR")
    sqlite_db_path: str = Field(default="backend/data/app.db", alias="SQLITE_DB_PATH")

    model_config = SettingsConfigDict(
        env_file=("backend/.env", "backend/.env.example"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

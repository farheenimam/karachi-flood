from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    gemini_api_key: str = ""
    meteosource_api_key: str = ""
    tomtom_api_key: str = ""
    firebase_credentials_path: str = "./firebase-credentials.json"
    firebase_project_id: str = ""
    log_level: str = "INFO"
    simulation_mode: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore")

    app_name: str = "API610 Smart Comparator"
    app_env: str = "dev"

    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    openai_timeout: int = 60

    kb_path: str = "data/知识库/标准化配套知识库.json"
    kb_dir: str = "data/知识库"
    logo_dir: str = "data/logo"
    temp_dir: str = "data/tmp"

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def kb_file(self) -> Path:
        return self.project_root / self.kb_path

    @property
    def kb_directory(self) -> Path:
        return self.project_root / self.kb_dir

    @property
    def logo_path(self) -> Path:
        return self.project_root / self.logo_dir

    @property
    def temp_path(self) -> Path:
        return self.project_root / self.temp_dir

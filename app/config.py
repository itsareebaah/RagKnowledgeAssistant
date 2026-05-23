from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    embedding_model: str = "all-MiniLM-L6-v2"
    chroma_path: str = "./data/chroma"
    upload_path: str = "./data/uploads"
    chunk_size: int = 800
    chunk_overlap: int = 150
    top_k: int = 5

    @property
    def chroma_dir(self) -> Path:
        path = Path(self.chroma_path)
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def upload_dir(self) -> Path:
        path = Path(self.upload_path)
        return path if path.is_absolute() else PROJECT_ROOT / path


settings = Settings()

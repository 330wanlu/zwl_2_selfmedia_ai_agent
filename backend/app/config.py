from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 数据库（本机原生 PostgreSQL 18）
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/media_agent"

    # 豆包（火山方舟，一个 Key 两个模型）
    ark_api_key: str = ""
    llm_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    llm_model: str = "doubao-seed-1-8-251228"
    image_model: str = "doubao-seedream-4-5-251128"

    # 调试
    debug: bool = True

    # 存储
    image_dir: str = "./data/images"

    @property
    def sync_database_url(self) -> str:
        """Alembic / PostgresSaver 使用的同步驱动连接串（psycopg3）。"""
        return self.database_url.replace("+asyncpg", "+psycopg")

    @property
    def image_dir_path(self) -> Path:
        p = Path(self.image_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()

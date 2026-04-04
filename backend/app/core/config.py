import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Data Analysis System"
    API_V1_STR: str = "/api/v1"
    
    # 存储相关配置
    STORAGE_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
    DB_FILE: str = "sqlite.db"
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        # SQLite 数据库文件存放在 STORAGE_DIR 目录下
        os.makedirs(self.STORAGE_DIR, exist_ok=True)
        return f"sqlite:///{os.path.join(self.STORAGE_DIR, self.DB_FILE)}"

    # 日志配置
    LOG_LEVEL: str = "INFO"

    # CORS 允许的来源
    BACKEND_CORS_ORIGINS: list[str] = ["*"]
    
    # 数据集存储目录
    DATA_DIR: str = "./data/datasets"

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env")

settings = Settings()

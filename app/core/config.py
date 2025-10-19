# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra="ignore"
    )

    APP_NAME: str = "mymap-2api"
    APP_VERSION: str = "1.0.0"
    DESCRIPTION: str = "一个将 mymap.ai 转换为兼容 OpenAI 格式 API 的高性能代理，支持上下文、思维导图和文件上传。"

    API_MASTER_KEY: Optional[str] = "1"
    
    API_REQUEST_TIMEOUT: int = 180
    NGINX_PORT: int = 8088
    SESSION_CACHE_TTL: int = 3600 # 会话缓存1小时

    # 模型配置
    DEFAULT_MODEL: str = "mymap-ai"
    KNOWN_MODELS: List[str] = ["mymap-ai", "mymap-ai-vision"]

settings = Settings()

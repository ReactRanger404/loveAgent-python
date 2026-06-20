"""配置管理 - 基于 Pydantic Settings"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # DashScope 配置
    dashscope_api_key: str = "sk-2186104e1f154b90beca9d7037ae1582"
    dashscope_model: str = "qwen-plus"
    dashscope_vision_model: str = "qwen-vl-max"
    dashscope_tts_model: str = "sambert-zhiqi-v1"
    dashscope_tts_voice: str = "longanyang"
    dashscope_asr_model: str = "paraformer-realtime-v2"

    # 搜索 API
    search_api_key: str = "mRB5yLiMcMhrdX92Vc5QLsDV"

    # Pexels 图片搜索
    pexels_api_key: str = "VBnKFHzthHM3JjpANqY3EvYaiUIfxnZCIfrTngcIJ9OrJoqDwbBhRxDI"

    # 高德地图
    amap_maps_api_key: str = "efec48c21522333bc75044afb1716bfd"

    # 服务器
    server_host: str = "0.0.0.0"
    server_port: int = 8123
    context_path: str = "/api"

    # PostgreSQL（本地）
    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5433
    postgres_user: str = "my_user"
    postgres_password: str = "20050828zxhH_"
    postgres_db: str = "ai_agent"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

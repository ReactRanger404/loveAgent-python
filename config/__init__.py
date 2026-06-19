"""配置管理 - 基于 Pydantic Settings"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # DashScope 配置
    dashscope_api_key: str = "sk-2186104e1f154b90beca9d7037ae1582"
    dashscope_model: str = "qwen-plus"
    dashscope_vision_model: str = "qwen-vl-max"
    dashscope_tts_model: str = "cosyvoice-v3-flash"
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

    # PostgreSQL（可选）
    postgres_url: Optional[str] = None
    postgres_user: Optional[str] = None
    postgres_password: Optional[str] = None

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

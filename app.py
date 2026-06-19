"""
AI Agent Python 版 - FastAPI 应用程序入口
对应 Java: AiAgentApplication.java

启动命令：python app.py
或：uvicorn app:app --host 0.0.0.0 --port 8123 --reload
"""
import logging
import sys

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_openai import ChatOpenAI
from langchain_core.tools import BaseTool

from config import settings
from config.constants import FILE_SAVE_DIR
from api.routes import create_router
from agents.manus import Manus
from apps.love_app import LoveApp
from tools import get_all_tools

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    创建并配置 FastAPI 应用
    对应 Java: SpringApplication.run(AiAgentApplication.class)
    """
    app = FastAPI(
        title="AI Agent",
        description="AI 智能体系统（Python 重构版）",
        version="1.0.0",
    )

    # ========== CORS 配置 ==========
    # 对应 Java: CorsConfig.java
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # ========== 初始化 LLM ==========
    # 使用 LangChain 的 ChatOpenAI 接口调用阿里云 DashScope
    # 兼容 OpenAI 格式的 API
    llm = ChatOpenAI(
        model=settings.dashscope_model,
        api_key=settings.dashscope_api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        temperature=0.7,
        streaming=True,
    )

    # 视觉模型
    vision_llm = ChatOpenAI(
        model=settings.dashscope_vision_model,
        api_key=settings.dashscope_api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        temperature=0.7,
    )

    # ========== 初始化工具 ==========
    all_tools: list[BaseTool] = get_all_tools(api_key=settings.search_api_key)

    # ========== 初始化应用 ==========
    # 恋爱大师应用（对应 Java LoveApp）
    love_app = LoveApp(
        llm=llm,
        retriever=None,  # 需要 ChromaDB 初始化后设置
        llm_for_rewrite=llm,
    )

    # Manus 超级智能体（对应 Java Manus）
    manus_agent = Manus(
        available_tools=all_tools,
        llm=llm,
    )

    # ========== 注册路由 ==========
    router = create_router(
        love_app=love_app,
        manus_agent=manus_agent,
        vision_llm=vision_llm,
    )
    app.include_router(router, prefix=settings.context_path)

    # ========== 确保目录存在 ==========
    import os
    os.makedirs(FILE_SAVE_DIR, exist_ok=True)
    os.makedirs(os.path.join(FILE_SAVE_DIR, "audio"), exist_ok=True)
    os.makedirs(os.path.join(FILE_SAVE_DIR, "pdf"), exist_ok=True)
    os.makedirs(os.path.join(FILE_SAVE_DIR, "download"), exist_ok=True)
    os.makedirs(os.path.join(FILE_SAVE_DIR, "temp_audio"), exist_ok=True)
    os.makedirs("./tmp/chroma_db", exist_ok=True)

    @app.on_event("startup")
    async def startup():
        logger.info("=" * 50)
        logger.info("AI Agent Python 版启动成功!")
        logger.info("服务地址: http://%s:%d%s", settings.server_host, settings.server_port, settings.context_path)
        logger.info("API 文档: http://%s:%d/docs", settings.server_host, settings.server_port)
        logger.info("=" * 50)

    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=False,
        log_level="info",
    )

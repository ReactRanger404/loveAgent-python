"""
AI Agent Python 版 - FastAPI 应用程序入口

启动：python app.py
"""
import logging
import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.tools import BaseTool

from config import settings
from config.constants import FILE_SAVE_DIR
from api.routes import create_router
from tools import get_all_tools

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    from contextlib import asynccontextmanager
    retriever_holder = {"instance": None}

    @asynccontextmanager
    async def lifespan(app_instance):
        # 初始化会话持久化数据库
        try:
            from chat_memory.db_storage import SessionStorage
            await SessionStorage.init()
            logger.info("会话持久化: SQLite")
        except Exception as e:
            logger.warning("会话持久化初始化失败（不影响基本功能）: %s", e)

        logger.info("=" * 50)
        logger.info("领域智能体启动成功!")
        logger.info("地址: http://%s:%d%s", settings.server_host, settings.server_port, settings.context_path)
        if retriever_holder["instance"]:
            try:
                r = retriever_holder["instance"]
                doc_count = len(r.vectorstore.get()['ids']) if hasattr(r, 'vectorstore') else 0
                logger.info("知识库: %d 篇文档", doc_count)
            except Exception:
                pass
        logger.info("=" * 50)
        yield

    app = FastAPI(title="AI Agent", description="领域智能体系统", version="1.0.0", lifespan=lifespan)

    # CORS
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"], expose_headers=["*"])

    # ========== LLM（主模型 + 备用模型自动切换） ==========
    llm_base = ChatOpenAI(
        model=settings.dashscope_model,
        api_key=settings.dashscope_api_key,
        base_url=settings.dashscope_base_url,
        temperature=0.7,
    )

    # 创建备用模型列表（阿里云 DashScope 备用模型）
    fallbacks = []
    for fb_model in settings.dashscope_fallback_models:
        fallbacks.append(ChatOpenAI(
            model=fb_model,
            api_key=settings.dashscope_api_key,
            base_url=settings.dashscope_base_url,
            temperature=0.7,
        ))
        logger.info("备用模型(阿里云): %s", fb_model)

    # 如果配置了 DeepSeek，也加入备用列表
    if settings.deepseek_api_key:
        fallbacks.append(ChatOpenAI(
            model=settings.deepseek_model,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            temperature=0.7,
        ))
        logger.info("备用模型(DeepSeek): %s", settings.deepseek_model)

    if fallbacks:
        llm = llm_base.with_fallbacks(fallbacks, exceptions_to_handle=(Exception,))
        logger.info("主模型: %s | 备用数: %d", settings.dashscope_model, len(fallbacks))
    else:
        llm = llm_base

    # ========== 工具 ==========
    all_tools = get_all_tools(api_key=settings.search_api_key)

    # ========== RAG 知识库 ==========
    try:
        embeddings = DashScopeEmbeddings(
            model="text-embedding-v3",
            dashscope_api_key=settings.dashscope_api_key,
        )
        from rag.vector_store import VectorStoreManager
        vs_mgr = VectorStoreManager(embedding_function=embeddings, persist_directory="./tmp/chroma_db", llm=llm)
        vs_mgr.initialize()
        retriever = vs_mgr.as_retriever(search_kwargs={"k": 3})
        retriever_holder["instance"] = retriever

        from tools.rag_query import set_retriever, set_llm
        set_retriever(retriever)
        set_llm(llm)
        logger.info("RAG 知识库加载成功")
    except Exception as e:
        logger.warning("RAG 知识库加载失败（不影响基本功能）: %s", e)

    # ========== 路由 ==========
    router = create_router(all_tools=all_tools, llm=llm)
    app.include_router(router, prefix=settings.context_path)

    # ========== 目录 ==========
    os.makedirs(FILE_SAVE_DIR, exist_ok=True)
    os.makedirs(os.path.join(FILE_SAVE_DIR, "audio"), exist_ok=True)
    os.makedirs(os.path.join(FILE_SAVE_DIR, "pdf"), exist_ok=True)
    os.makedirs(os.path.join(FILE_SAVE_DIR, "download"), exist_ok=True)
    os.makedirs("./tmp/chroma_db", exist_ok=True)

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run("app:app", host=settings.server_host, port=settings.server_port, log_level="info")

"""RAG 知识库查询工具 - 供智能体调用"""
import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import tool

from rag.query_rewriter import QueryRewriter

logger = logging.getLogger(__name__)

# 将在 app.py 初始化时设置
_retriever = None
_llm: BaseChatModel | None = None


def set_retriever(retriever):
    """设置向量检索器（由 app.py 初始化时调用）"""
    global _retriever
    _retriever = retriever
    logger.info("RAG 检索器已注入工具")


def set_llm(llm: BaseChatModel):
    """设置 LLM（用于查询重写，由 app.py 初始化时调用）"""
    global _llm
    _llm = llm
    logger.info("RAG 查询重写 LLM 已注入工具")


@tool
def rag_query(query: str) -> str:
    """
    Search the domain knowledge base for love/relationship advice.
    Use this when you need expert knowledge about dating, relationships, or marriage.
    :param query: The question or topic to search for
    :return: Relevant knowledge base content
    """
    if _retriever is None:
        return "知识库未初始化"

    try:
        # 查询重写：口语→专业，提升检索命中率
        if _llm is not None:
            rewritten = QueryRewriter(_llm).rewrite(query)
            logger.info("查询重写: %s -> %s", query, rewritten)
        else:
            rewritten = query

        docs = _retriever.invoke(rewritten)
        if not docs:
            return "知识库中未找到相关信息"

        results = []
        for i, doc in enumerate(docs, 1):
            content = doc.page_content if hasattr(doc, "page_content") else str(doc)
            results.append(f"[{i}] {content[:500]}")

        return "\n\n".join(results)
    except Exception as e:
        logger.error("RAG 查询失败: %s", e)
        return f"知识库查询出错: {e!s}"


rag_query_tool = rag_query

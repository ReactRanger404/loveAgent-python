"""查询重写器 - 对应 Java 的 QueryRewriter"""
import logging

from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)


class QueryRewriter:
    """
    查询重写器 —— 让用户的问题通过 AI 变得更加专业
    对应 Java: QueryRewriter.java (基于 RewriteQueryTransformer)
    """

    def __init__(self, llm: BaseChatModel):
        self._llm = llm

    def rewrite(self, query: str) -> str:
        """
        执行查询重写
        对应 Java: doQueryRewrite(String prompt)
        """
        prompt = (
            f"你是一个专业的查询重写助手。请将用户的原始问题改写得更专业、更清晰、"
            f"更利于信息检索。保持原始意图不变，但补充必要的上下文信息。\n\n"
            f"原始问题：{query}\n\n改写后："
        )
        try:
            response = self._llm.invoke(prompt)
            rewritten = response.content.strip() if hasattr(response, 'content') else str(response).strip()
            logger.info("查询重写：%s -> %s", query, rewritten)
            return rewritten
        except Exception as e:
            logger.warning("查询重写失败，使用原问题: %s", e)
            return query

"""AI 关键词元信息增强器 - 对应 Java 的 MyKeywordEnricher"""
import logging
from typing import Optional

from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)


class KeywordEnricher:
    """
    基于 AI 的文档元信息增强器，为文档补充关键词
    对应 Java: MyKeywordEnricher.java (基于 KeywordMetadataEnricher)
    """

    def __init__(self, llm: Optional[BaseChatModel] = None):
        self._llm = llm

    def enrich_documents(self, documents: list[Document], keywords_count: int = 5) -> list[Document]:
        """
        为文档补充关键词元信息
        对应 Java: enrichDocuments()
        """
        enriched = []
        for doc in documents:
            if self._llm and doc.page_content:
                try:
                    prompt = (
                        f"从以下文本中提取 {keywords_count} 个最关键的关键词，"
                        f"用逗号分隔返回。\n\n文本：{doc.page_content[:500]}"
                    )
                    response = self._llm.invoke(prompt)
                    keywords = response.content.strip() if hasattr(response, 'content') else str(response).strip()
                    doc.metadata["keywords"] = keywords
                except Exception as e:
                    logger.warning("关键词生成失败: %s", e)
                    doc.metadata["keywords"] = ""
            enriched.append(doc)
        return enriched

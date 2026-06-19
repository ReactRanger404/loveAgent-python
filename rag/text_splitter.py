"""文本切分器 - 对应 Java 的 MyTokenTextSplitter"""
import logging

from langchain_text_splitters import TokenTextSplitter
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class TextSplitter:
    """
    自定义基于 Token 的文本切分器
    对应 Java: MyTokenTextSplitter.java
    """

    @staticmethod
    def split_documents(documents: list[Document]) -> list[Document]:
        """使用默认参数切分文档"""
        splitter = TokenTextSplitter()
        return splitter.split_documents(documents)

    @staticmethod
    def split_customized(documents: list[Document]) -> list[Document]:
        """使用自定义参数切分文档"""
        splitter = TokenTextSplitter(
            chunk_size=200,
            chunk_overlap=100,
            encoding_name="cl100k_base",
        )
        return splitter.split_documents(documents)

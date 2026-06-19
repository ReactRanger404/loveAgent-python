"""向量存储配置 - 对应 Java 的 LoveAppVectorStoreConfig"""
import logging
from typing import Optional

from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore

from rag.document_loader import DocumentLoader
from rag.keyword_enricher import KeywordEnricher
from rag.text_splitter import TextSplitter

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """
    向量数据库管理器（基于 ChromaDB）
    对应 Java: LoveAppVectorStoreConfig.java + PgVectorVectorStoreConfig.java
    """

    def __init__(
        self,
        embedding_function: Embeddings,
        persist_directory: str = "./tmp/chroma_db",
        llm=None,
    ):
        self._embedding_function = embedding_function
        self._persist_directory = persist_directory
        self._llm = llm
        self._vector_store: Optional[VectorStore] = None

    def initialize(self) -> VectorStore:
        """初始化向量存储：加载文档、切分、增强、存入 ChromaDB"""
        # 1. 加载文档
        loader = DocumentLoader()
        documents = loader.load_documents()

        # 2. 切分文档
        splitter = TextSplitter()
        split_docs = splitter.split_customized(documents)

        # 3. 关键词增强
        if self._llm:
            enricher = KeywordEnricher(self._llm)
            split_docs = enricher.enrich_documents(split_docs)

        # 4. 存入 ChromaDB
        self._vector_store = Chroma.from_documents(
            documents=split_docs,
            embedding=self._embedding_function,
            persist_directory=self._persist_directory,
        )
        logger.info(
            "向量存储初始化完成: %d 个文档, 存储位置: %s",
            len(split_docs),
            self._persist_directory,
        )
        return self._vector_store

    def get_vector_store(self) -> Optional[VectorStore]:
        return self._vector_store

    def as_retriever(self, **kwargs):
        if self._vector_store is None:
            self.initialize()
        return self._vector_store.as_retriever(**kwargs)

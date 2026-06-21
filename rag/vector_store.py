"""向量存储配置 - 对应 Java 的 LoveAppVectorStoreConfig"""
import logging
from typing import Optional

from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore

from rag.document_loader import DocumentLoader, PDFLoader
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
        # 先尝试加载已有 ChromaDB，避免重复添加
        try:
            existing = Chroma(
                embedding_function=self._embedding_function,
                persist_directory=self._persist_directory,
            )
            if existing._collection.count() > 0:
                self._vector_store = existing
                logger.info("加载已有知识库: %d 篇文档", existing._collection.count())
                return self._vector_store
        except Exception:
            pass

        # 首次初始化：加载文档（md + pdf）、切分、增强、存入 ChromaDB
        loader = DocumentLoader()
        documents = loader.load_documents()

        pdf_loader = PDFLoader()
        pdf_docs = pdf_loader.load_documents(describe_images=True)

        splitter = TextSplitter()
        split_docs = splitter.split_customized(documents)

        if pdf_docs:
            pdf_chunks = splitter.split_pdf_documents(pdf_docs)
            split_docs.extend(pdf_chunks)
            logger.info("合并 PDF 知识库: %d 个 chunk", len(pdf_chunks))

        if self._llm:
            enricher = KeywordEnricher(self._llm)
            split_docs = enricher.enrich_documents(split_docs)

        self._vector_store = Chroma.from_documents(
            documents=split_docs,
            embedding=self._embedding_function,
            persist_directory=self._persist_directory,
        )
        logger.info(
            "知识库初始化完成: %d 篇文档 → %s",
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

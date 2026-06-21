"""文本切分器 - 按 Markdown 标题层级切分 + Token 二次切分"""
import logging

from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    TokenTextSplitter,
)
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class TextSplitter:
    """
    基于标题层级的 Markdown 文档切割器
    - 先按标题层级（# → ## → ### → ####）把文档切成有结构的块
    - 再对过长的块做 Token 级别的二次切分
    对应 Java: MyTokenTextSplitter.java
    """

    # 要按层级切分的标题（从高到低）
    HEADERS_TO_SPLIT_ON = [
        ("#", "h1"),
        ("##", "h2"),
        ("###", "h3"),
        ("####", "h4"),
        ("#####", "h5"),
    ]

    @staticmethod
    def split_documents(documents: list[Document]) -> list[Document]:
        """使用默认参数切分文档"""
        return TextSplitter._split_with_headers(
            documents,
            chunk_size=400,
            chunk_overlap=50,
        )

    @staticmethod
    def split_customized(documents: list[Document]) -> list[Document]:
        """使用自定义参数切分文档"""
        return TextSplitter._split_with_headers(
            documents,
            chunk_size=200,
            chunk_overlap=100,
        )

    @staticmethod
    def _split_with_headers(
        documents: list[Document],
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[Document]:
        """
        先用 MarkdownHeaderTextSplitter 按标题结构切分，
        再对过长块用 TokenTextSplitter 二次切分。
        """
        md_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=TextSplitter.HEADERS_TO_SPLIT_ON,
            strip_headers=False,
        )
        token_splitter = TokenTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            encoding_name="cl100k_base",
        )

        all_chunks: list[Document] = []
        for doc in documents:
            # 第 1 步：按标题层级切分
            try:
                header_chunks = md_splitter.split_text(doc.page_content)
            except Exception as e:
                logger.warning("MarkdownHeaderTextSplitter 失败: %s，回退全文", e)
                header_chunks = [Document(page_content=doc.page_content)]

            for hc in header_chunks:
                # 合并文件级元信息 + 标题层级元信息
                merged_meta = {**doc.metadata, **hc.metadata}

                # 第 2 步：对过长的块做 Token 二次切分
                if len(hc.page_content) > chunk_size * 2:
                    sub_chunks = token_splitter.split_documents(
                        [Document(page_content=hc.page_content, metadata=merged_meta)]
                    )
                    for sc in sub_chunks:
                        sc.metadata = {**sc.metadata, **merged_meta}
                    all_chunks.extend(sub_chunks)
                else:
                    all_chunks.append(
                        Document(page_content=hc.page_content, metadata=merged_meta)
                    )

        logger.info(
            "TextSplitter: %d docs → %d chunks (size=%d, overlap=%d)",
            len(documents),
            len(all_chunks),
            chunk_size,
            chunk_overlap,
        )
        return all_chunks

"""文档加载器 - 对应 Java 的 LoveAppDocumentLoader"""
import os
import glob
import logging

from langchain_core.documents import Document

from config.constants import DOCUMENTS_DIR

logger = logging.getLogger(__name__)


class DocumentLoader:
    """
    恋爱大师应用文档加载器
    对应 Java: LoveAppDocumentLoader.java
    """

    @staticmethod
    def load_documents() -> list[Document]:
        """
        加载多篇 md 文档（原始内容，不做切割）
        由 TextSplitter 使用 MarkdownHeaderTextSplitter 按标题层级切割
        对应 Java: loadDocuments()
        """
        all_documents = []
        md_files = glob.glob(os.path.join(DOCUMENTS_DIR, "*.md"))

        for file_path in md_files:
            filename = os.path.basename(file_path)
            # 从文件名提取状态信息（如 "单身篇" -> "单身"）
            status = filename.replace("恋爱常见问题和回答 - ", "").replace(".md", "")

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            doc = Document(
                page_content=content,
                metadata={
                    "filename": filename,
                    "status": status,
                },
            )
            all_documents.append(doc)

        logger.info("Loaded %d documents from %s", len(all_documents), DOCUMENTS_DIR)
        return all_documents

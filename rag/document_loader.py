"""文档加载器 - md + PDF 双通道"""
import os
import glob
import logging

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader

from config.constants import DOCUMENTS_DIR

logger = logging.getLogger(__name__)


class DocumentLoader:
    """
    恋爱大师应用文档加载器（.md）
    对应 Java: LoveAppDocumentLoader.java
    """

    @staticmethod
    def load_documents() -> list[Document]:
        """
        加载多篇 md 文档（原始内容，不做切割）
        由 TextSplitter 使用 MarkdownHeaderTextSplitter 按标题层级切割
        """
        all_documents = []
        md_files = glob.glob(os.path.join(DOCUMENTS_DIR, "*.md"))

        for file_path in md_files:
            filename = os.path.basename(file_path)
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

        logger.info("Loaded %d md documents from %s", len(all_documents), DOCUMENTS_DIR)
        return all_documents


class PDFLoader:
    """
    PDF 文档加载器（新增，与 md 互不干扰）

    使用 LangChain 的 PyPDFLoader 按页提取文本，
    可选：调用 ImageProcessor 提取嵌入图片并用 Qwen-VL 描述，
    描述文字自动合并到对应页的文本中。
    """

    def __init__(self, pdf_dir: str = None):
        self.pdf_dir = pdf_dir or os.path.join(DOCUMENTS_DIR, "pdf")

    def load_documents(
        self,
        describe_images: bool = False,
    ) -> list[Document]:
        """
        扫描 pdf_dir 下的所有 .pdf 文件，
        每个 PDF 按页提取，返回 List[Document]。

        :param describe_images: 是否启用图片识别（调用 Qwen-VL 描述嵌入图片）
        """
        if not os.path.isdir(self.pdf_dir):
            logger.warning("PDF 目录不存在: %s", self.pdf_dir)
            return []

        pdf_files = glob.glob(os.path.join(self.pdf_dir, "*.pdf"))

        # 延迟导入，避免没装 pymupdf 时直接报错
        image_processor = None
        if describe_images:
            try:
                from rag.image_processor import ImageProcessor
                image_processor = ImageProcessor()
                if not image_processor.enabled:
                    image_processor = None
            except ImportError as e:
                logger.warning("图片识别不可用（请安装 pymupdf）: %s", e)

        all_documents: list[Document] = []

        for file_path in pdf_files:
            filename = os.path.basename(file_path)
            try:
                loader = PyPDFLoader(file_path)
                pages = loader.load()
                for page in pages:
                    page.metadata["filename"] = filename
                    page.metadata["file_path"] = file_path

                # 可选：为每页补充图片描述
                if image_processor:
                    image_descs = image_processor.process_pdf(file_path)
                    for page in pages:
                        page_num = page.metadata.get("page", 0)
                        desc = image_descs.get(page_num)
                        if desc:
                            page.page_content += "\n\n" + desc
                            page.metadata["has_image_desc"] = True

                all_documents.extend(pages)
                logger.info(
                    "  PDF: %s → %d 页%s",
                    filename, len(pages),
                    "（含图片描述）" if image_processor else "",
                )
            except Exception as e:
                logger.error("  PDF 加载失败 %s: %s", filename, e)

        logger.info(
            "PDFLoader: %d 个文件 → %d 个 Document",
            len(pdf_files), len(all_documents),
        )
        return all_documents

"""文本切分器 - 按 Markdown 标题层级切分 + 递归字符二次切分"""
import logging

from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class TextSplitter:
    """
    基于标题层级的 Markdown 文档切割器

    策略：
    1. 先按标题层级（# → ## → ### → ####）把文档切成有结构的块
       — 每个问答题完整保留，不断句
    2. 如果一个标题下面内容过长（> max_chunk_chars），
       用 RecursiveCharacterTextSplitter 二次切分
       — 优先保段落（\n\n），保不住才保句子（。！？）
       — 每个子 chunk 继承原标题层级元信息

    对应 Java: MyTokenTextSplitter.java
    """

    HEADERS_TO_SPLIT_ON = [
        ("#", "h1"),
        ("##", "h2"),
        ("###", "h3"),
        ("####", "h4"),
        ("#####", "h5"),
    ]

    @staticmethod
    def split_documents(documents: list[Document]) -> list[Document]:
        return TextSplitter._split_with_headers(
            documents, max_chunk_chars=800, chunk_overlap=100
        )

    @staticmethod
    def split_customized(documents: list[Document]) -> list[Document]:
        return TextSplitter._split_with_headers(
            documents, max_chunk_chars=500, chunk_overlap=100
        )

    # ──────────────────────────────────────────────
    # PDF 专用切分（无 md 标题，直接按字符段落切）
    # ──────────────────────────────────────────────

    @staticmethod
    def split_pdf_documents(
        documents: list[Document],
        chunk_size: int = 500,
        chunk_overlap: int = 100,
    ) -> list[Document]:
        """
        PDF 文档切分（不经过 MarkdownHeaderTextSplitter）。

        策略：
        1. 同一 PDF 的连续页面先合并（避免切出半页碎片）
        2. 按 RecursiveCharacterTextSplitter 切分（段落 → 句子 → 字符）
        3. 合并过小 chunk
        """
        min_chunk_chars = 100

        char_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", "，", " ", ""],
            keep_separator=True,
        )

        # 按文件分组，组内按页码排序
        from collections import defaultdict
        by_file: dict[str, list[Document]] = defaultdict(list)
        for d in documents:
            by_file[d.metadata.get("filename", "unknown")].append(d)

        all_chunks: list[Document] = []
        for fname, pages in by_file.items():
            # 同一文件的页面排序
            pages.sort(key=lambda p: p.metadata.get("page", 0))
            # 合并所有页到一个字符串（保留页码边界标记）
            full_text = "\n\n".join(p.page_content for p in pages)
            merged_meta = {
                "filename": fname,
                "source_type": "pdf",
                "pages": "%d-%d" % (
                    pages[0].metadata.get("page", 0) + 1,
                    pages[-1].metadata.get("page", 0) + 1,
                ) if len(pages) > 1 else str(pages[0].metadata.get("page", 0) + 1),
            }

            # 按字符切分
            sub_chunks = char_splitter.split_documents([
                Document(page_content=full_text)
            ])
            for sc in sub_chunks:
                sc.metadata = dict(merged_meta)
            all_chunks.extend(sub_chunks)

        # 合并过小 chunk
        merged: list[Document] = []
        for c in all_chunks:
            if not merged:
                merged.append(c)
                continue
            last = merged[-1]
            if len(c.page_content) < min_chunk_chars or len(last.page_content) < min_chunk_chars:
                last.page_content += "\n\n" + c.page_content
                # 更新页码范围
                last.metadata["pages"] = last.metadata.get("pages", "?")
            else:
                merged.append(c)

        logger.info(
            "PDFTextSplitter: %d pages → %d chunks (size=%d, overlap=%d)",
            len(documents), len(merged), chunk_size, chunk_overlap,
        )
        return merged

    @staticmethod
    def _split_with_headers(
        documents: list[Document],
        max_chunk_chars: int,
        chunk_overlap: int,
    ) -> list[Document]:
        """
        第一刀：按标题结构切
        第二刀：对超长段落递归切（\n\n → \n → 句号 → 字符）
        第三刀：合并过小的相邻 chunk（< min_chunk_chars），避免碎片
        """
        min_chunk_chars = 100  # 低于此值的 chunk 会被合入下一个

        md_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=TextSplitter.HEADERS_TO_SPLIT_ON,
            strip_headers=False,
        )
        char_splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chunk_chars,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", "，", " ", ""],
            keep_separator=True,
        )

        all_chunks: list[Document] = []
        for doc in documents:
            try:
                header_chunks = md_splitter.split_text(doc.page_content)
            except Exception as e:
                logger.warning("MarkdownHeaderTextSplitter 失败: %s，回退全文", e)
                header_chunks = [Document(page_content=doc.page_content)]

            for hc in header_chunks:
                merged_meta = {**doc.metadata, **hc.metadata}

                if len(hc.page_content) <= max_chunk_chars:
                    all_chunks.append(
                        Document(page_content=hc.page_content, metadata=merged_meta)
                    )
                else:
                    sub_chunks = char_splitter.split_documents([
                        Document(page_content=hc.page_content)
                    ])
                    for sc in sub_chunks:
                        sc.metadata = dict(merged_meta)
                    all_chunks.extend(sub_chunks)

        # ---- 第三刀：合并过小的相邻 chunk ----
        merged: list[Document] = []
        for c in all_chunks:
            if not merged:
                # 用列表存储所有被合并的 h4
                h4_val = c.metadata.get('h4')
                c.metadata['h4_list'] = [h4_val] if h4_val else []
                merged.append(c)
                continue

            last = merged[-1]
            if len(c.page_content) < min_chunk_chars or len(last.page_content) < min_chunk_chars:
                last.page_content += "\n\n" + c.page_content
                h4_val = c.metadata.get('h4')
                if h4_val and h4_val not in last.metadata.get('h4_list', []):
                    last.metadata.setdefault('h4_list', []).append(h4_val)
            else:
                h4_val = c.metadata.get('h4')
                c.metadata['h4_list'] = [h4_val] if h4_val else []
                merged.append(c)

        # 刷新 h4 字段：合并后的 chunk 标注涵盖的问题数
        for m in merged:
            h4_list = m.metadata.get('h4_list', [])
            if len(h4_list) > 1:
                m.metadata['h4'] = "%s 等%d个问题" % (h4_list[0], len(h4_list))
            elif len(h4_list) == 1:
                m.metadata['h4'] = h4_list[0]

        logger.info(
            "TextSplitter: %d docs → %d raw → %d final (max=%d, min=%d, overlap=%d)",
            len(documents), len(all_chunks), len(merged),
            max_chunk_chars, min_chunk_chars, chunk_overlap,
        )
        return merged

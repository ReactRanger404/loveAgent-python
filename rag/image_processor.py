"""PDF 图片提取 + 多模态 LLM 描述（可选）
依赖: pymupdf (fitz), dashscope (qwen-vl-max)
"""
import base64
import io
import logging
import os
from typing import Optional

import fitz  # PyMuPDF

from config import settings

logger = logging.getLogger(__name__)


class ImageProcessor:
    """
    PDF 图片处理器

    1. 用 PyMuPDF 打开 PDF，逐页提取嵌入的图片
    2. 将图片转 base64，调用 Qwen-VL 获取文字描述
    3. 返回每页的图片描述文本
    """

    def __init__(
        self,
        vision_model: Optional[str] = None,
        api_key: Optional[str] = None,
        enabled: bool = True,
    ):
        self.vision_model = vision_model or settings.dashscope_vision_model
        self.api_key = api_key or settings.dashscope_api_key
        self.enabled = enabled

        if not self.api_key:
            logger.warning("ImageProcessor: 未配置 API Key，已禁用")
            self.enabled = False

    def process_pdf(self, pdf_path: str) -> dict[int, str]:
        """
        处理一个 PDF，返回 {页码: 图片描述文本} 的字典

        :param pdf_path: PDF 文件路径
        :return: 页码从 0 开始，描述文本可能为空
        """
        if not self.enabled:
            return {}

        result: dict[int, str] = {}
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            logger.error("无法打开 PDF %s: %s", pdf_path, e)
            return result

        for page_num in range(len(doc)):
            page = doc[page_num]
            images = page.get_images(full=True)
            if not images:
                continue  # 该页无嵌入图片

            descriptions: list[str] = []
            for img_idx, img_info in enumerate(images):
                xref = img_info[0]
                try:
                    pix = fitz.Pixmap(doc, xref)
                    desc = self._describe_image(pix, page_num, img_idx)
                    if desc:
                        descriptions.append("[图片描述: %s]" % desc)
                except Exception as e:
                    logger.warning("图片提取失败 page=%d img=%d: %s", page_num, img_idx, e)

            if descriptions:
                result[page_num] = "\n".join(descriptions)

        doc.close()
        logger.info(
            "ImageProcessor: %s → %d 页含图片描述",
            os.path.basename(pdf_path), len(result),
        )
        return result

    def _describe_image(
        self, pix: fitz.Pixmap, page_num: int, img_idx: int
    ) -> Optional[str]:
        """
        将图片发送给 Qwen-VL，返回文字描述

        :param pix: PyMuPDF 图片对象
        :return: 描述文本，失败返回 None
        """
        # 过小的图片（图标、装饰）跳过
        if pix.width < 100 or pix.height < 100:
            logger.debug("跳过过小图片: %dx%d", pix.width, pix.height)
            return None

        # 转 JPEG（压缩，节省 token）
        img_bytes = pix.tobytes("jpeg")
        b64 = base64.b64encode(img_bytes).decode()

        try:
            from dashscope import MultiModalConversation

            messages = [{
                "role": "user",
                "content": [
                    {"image": "data:image/jpeg;base64," + b64},
                    {"text": "请详细描述这张图片中的内容，包括文字、图表、数据等所有可见信息。"},
                ],
            }]

            response = MultiModalConversation.call(
                model=self.vision_model,
                messages=messages,
                api_key=self.api_key,
                max_tokens=500,
            )

            if response.status_code == 200:
                content = response.output.choices[0].message.content[0]["text"]
                logger.debug(
                    "图片描述 page=%d img=%d: %s...",
                    page_num, img_idx, content[:60],
                )
                return content
            else:
                logger.warning(
                    "Qwen-VL 返回异常 status=%s: %s",
                    response.status_code, response,
                )
                return None

        except Exception as e:
            logger.warning("Qwen-VL 调用失败 page=%d img=%d: %s", page_num, img_idx, e)
            return None

"""PDF 生成工具 - 使用 Windows 系统字体支持中文"""
import os
import logging

from fpdf import FPDF
from langchain_core.tools import tool

from config.constants import FILE_SAVE_DIR

logger = logging.getLogger(__name__)

# Windows 常见中文字体路径
_WINDOWS_FONTS = [
    r"C:\Windows\Fonts\msyh.ttc",     # 微软雅黑
    r"C:\Windows\Fonts\simsun.ttc",   # 宋体
    r"C:\Windows\Fonts\msyhbd.ttc",   # 微软雅黑加粗
    r"C:\Windows\Fonts\SIMKAI.ttf",   # 楷体
    r"C:\Windows\Fonts\SIMFANG.ttf",  # 仿宋
]


def _find_chinese_font() -> tuple[str, str]:
    """查找系统中可用的中文字体，返回 (路径, 名称)"""
    for font_path in _WINDOWS_FONTS:
        if os.path.exists(font_path):
            name = os.path.splitext(os.path.basename(font_path))[0]
            return font_path, name
    return "", ""


class ChinesePDF(FPDF):
    """支持中文的 PDF 类"""

    def __init__(self):
        super().__init__()
        self._cn_font = "Helvetica"
        font_path, font_name = _find_chinese_font()
        if font_path:
            try:
                self.add_font(font_name, "", font_path, uni=True)
                self._cn_font = font_name
            except Exception as e:
                logger.warning("加载中文字体失败: %s", e)

    def write_cn(self, text: str, size: int = 12):
        """写入中文文本"""
        self.set_font(self._cn_font, size=size)
        self.multi_cell(0, 10, text)


@tool
def generate_pdf(file_name: str, content: str) -> str:
    """
    Generate a PDF file with given content.
    :param file_name: Name of the file to save the generated PDF
    :param content: Content to be included in the PDF
    :return: Success or error message
    """
    file_dir = os.path.join(FILE_SAVE_DIR, "pdf")
    file_path = os.path.join(file_dir, file_name)
    try:
        os.makedirs(file_dir, exist_ok=True)
        pdf = ChinesePDF()
        pdf.add_page()
        pdf.write_cn(content)
        pdf.output(file_path)
        return f"PDF generated successfully to: {file_path}"
    except Exception as e:
        return f"Error generating PDF: {e!s}"


pdf_generation_tool = generate_pdf

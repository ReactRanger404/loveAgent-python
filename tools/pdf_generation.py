"""PDF 生成工具 """
import os
import logging

from fpdf import FPDF
from langchain_core.tools import tool

from config.constants import FILE_SAVE_DIR

logger = logging.getLogger(__name__)


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
        pdf = FPDF()
        pdf.add_page()
        # 添加中文字体支持
        pdf.add_font("SimSun", "", os.path.join(os.path.dirname(__file__), "..", "fonts", "simsun.ttf"),
                     uni=True) if os.path.exists(os.path.join(os.path.dirname(__file__), "..", "fonts", "simsun.ttf")) else None
        pdf.set_font("Helvetica", size=12)
        # 使用 multi_cell 处理多行文本
        pdf.multi_cell(0, 10, content.encode("latin-1", errors="replace").decode("latin-1"))
        pdf.output(file_path)
        return f"PDF generated successfully to: {file_path}"
    except Exception as e:
        return f"Error generating PDF: {e!s}"


pdf_generation_tool = generate_pdf

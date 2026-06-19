"""文件操作工具 - 对应 Java 的 FileOperationTool"""
import os
import logging

from langchain_core.tools import tool

from config.constants import FILE_SAVE_DIR

logger = logging.getLogger(__name__)


@tool
def read_file(file_name: str) -> str:
    """
    Read content from a file.
    :param file_name: Name of the file to read
    :return: File content as string
    """
    file_path = os.path.join(FILE_SAVE_DIR, file_name)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e!s}"


@tool
def write_file(file_name: str, content: str) -> str:
    """
    Write content to a file.
    :param file_name: Name of the file to write
    :param content: Content to write to the file
    :return: Success or error message
    """
    file_path = os.path.join(FILE_SAVE_DIR, file_name)
    try:
        os.makedirs(FILE_SAVE_DIR, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to the file: {file_path}"
    except Exception as e:
        return f"Error writing file: {e!s}"


file_read_tool = read_file
file_write_tool = write_file

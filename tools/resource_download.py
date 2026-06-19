"""资源下载工具 - 对应 Java 的 ResourceDownloadTool"""
import os
import logging

import httpx
from langchain_core.tools import tool

from config.constants import FILE_SAVE_DIR

logger = logging.getLogger(__name__)


@tool
def download_resource(url: str, file_name: str) -> str:
    """
    Download a resource from a given URL.
    :param url: URL of the resource to download
    :param file_name: Name of the file to save the downloaded resource
    :return: Success or error message
    """
    file_dir = os.path.join(FILE_SAVE_DIR, "download")
    file_path = os.path.join(file_dir, file_name)
    try:
        os.makedirs(file_dir, exist_ok=True)
        response = httpx.get(url, timeout=60, follow_redirects=True)
        response.raise_for_status()
        with open(file_path, "wb") as f:
            f.write(response.content)
        return f"Resource downloaded successfully to: {file_path}"
    except Exception as e:
        return f"Error downloading resource: {e!s}"


resource_download_tool = download_resource

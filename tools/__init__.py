"""
工具注册模块
对应 Java: ToolRegistration.java

集中注册所有工具，返回工具列表供智能体使用。
"""
from typing import Optional

from langchain_core.tools import BaseTool

from tools.file_operation import file_read_tool, file_write_tool
from tools.web_search import web_search_tool
from tools.web_scraping import web_scraping_tool
from tools.resource_download import resource_download_tool
from tools.terminal_operation import terminal_command_tool
from tools.pdf_generation import pdf_generation_tool
from tools.speech_recognition import speech_recognition_tool
from tools.speech_synthesis import speech_synthesis_tool
from tools.terminate import terminate_tool
from tools.rag_query import rag_query_tool


def get_all_tools(api_key: Optional[str] = None) -> list[BaseTool]:
    """
    获取所有已注册的工具
    对应 Java: ToolRegistration.allTools()
    """
    return [
        file_read_tool,
        file_write_tool,
        web_search_tool(api_key) if api_key else web_search_tool(),
        web_scraping_tool,
        resource_download_tool,
        terminal_command_tool,
        pdf_generation_tool,
        speech_recognition_tool,
        speech_synthesis_tool,
        rag_query_tool,
        terminate_tool,
    ]


__all__ = ["get_all_tools"]

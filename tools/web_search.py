"""网页搜索工具 - 对应 Java 的 WebSearchTool"""
import json
import logging
from typing import Optional

import httpx
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

SEARCH_API_URL = "https://www.searchapi.io/api/v1/search"


def create_web_search(api_key: Optional[str] = None):
    """
    创建网页搜索工具（工厂函数，支持注入 api_key）
    对应 Java: WebSearchTool(String apiKey)
    """

    @tool
    def search_web(query: str) -> str:
        """
        Search for information from Baidu Search Engine.
        :param query: Search query keyword
        :return: Search results as string
        """
        params = {
            "q": query,
            "api_key": api_key,
            "engine": "baidu",
        }
        try:
            response = httpx.get(SEARCH_API_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            organic_results = data.get("organic_results", [])
            top_results = organic_results[:5]
            return json.dumps(top_results, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"Error searching Baidu: {e!s}"

    return search_web


web_search_tool = create_web_search

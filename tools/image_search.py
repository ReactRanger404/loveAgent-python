"""图片搜索工具 - 对应 Java ImageSearchTool 在 ai-agent-image-server 中"""
import json
import logging

import httpx
from langchain_core.tools import tool

from config import settings

logger = logging.getLogger(__name__)

PEXELS_API_URL = "https://api.pexels.com/v1/search"


@tool
def search_image(query: str) -> str:
    """
    Search images from the web using Pexels API.
    :param query: Search query keyword
    :return: List of image URLs
    """
    try:
        headers = {"Authorization": settings.pexels_api_key}
        params = {"query": query, "per_page": 5}

        response = httpx.get(PEXELS_API_URL, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        # 提取图片 URL
        photos = data.get("photos", [])
        results = []
        for photo in photos:
            src = photo.get("src", {})
            results.append({
                "medium": src.get("medium"),
                "original": src.get("original"),
                "photographer": photo.get("photographer"),
            })

        return json.dumps(results, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error searching image: {e!s}"


image_search_tool = search_image

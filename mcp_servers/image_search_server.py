"""
图片搜索 MCP 服务器（独立进程）
对应 Java: ai-agent-image-server 中的 ImageSearchTool

可通过标准 I/O 作为 MCP 服务器运行，供主应用调用。
"""
import json
import sys
import logging

import httpx
from config import settings

logger = logging.getLogger(__name__)

PEXELS_API_URL = "https://api.pexels.com/v1/search"


def handle_request(request: dict) -> dict:
    """处理 MCP 请求"""
    action = request.get("action", "")
    params = request.get("params", {})

    if action == "search_image":
        query = params.get("query", "")
        try:
            headers = {"Authorization": settings.pexels_api_key}
            response = httpx.get(
                PEXELS_API_URL,
                headers=headers,
                params={"query": query, "per_page": 5},
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
            photos = data.get("photos", [])
            results = []
            for photo in photos:
                src = photo.get("src", {})
                results.append({
                    "medium": src.get("medium"),
                    "original": src.get("original"),
                    "photographer": photo.get("photographer"),
                })
            return {"status": "success", "data": results}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    return {"status": "error", "message": f"Unknown action: {action}"}


def main():
    """通过标准 I/O 运行 MCP 服务器"""
    logger.info("Image Search MCP Server starting...")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()
        except json.JSONDecodeError as e:
            error_response = {"status": "error", "message": f"Invalid JSON: {e}"}
            sys.stdout.write(json.dumps(error_response) + "\n")
            sys.stdout.flush()
        except Exception as e:
            error_response = {"status": "error", "message": str(e)}
            sys.stdout.write(json.dumps(error_response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()

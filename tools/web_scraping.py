"""网页抓取工具 - 对应 Java 的 WebScrapingTool"""
import logging

import httpx
from bs4 import BeautifulSoup
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def scrape_web_page(url: str) -> str:
    """
    Scrape the content of a web page.
    :param url: URL of the web page to scrape
    :return: HTML content of the page
    """
    try:
        response = httpx.get(url, timeout=15, follow_redirects=True)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        return soup.get_text(separator="\n", strip=True)[:10000]
    except Exception as e:
        return f"Error scraping web page: {e!s}"


web_scraping_tool = scrape_web_page

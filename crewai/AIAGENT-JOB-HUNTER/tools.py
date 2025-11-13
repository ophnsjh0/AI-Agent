import os, re
import requests
from crewai.tools import tool

# query = "네이버 주가"

@tool
def web_search_tool(query: str):
    """
    Firecrawl API를 사용하여 웹 검색을 수행하는 도구.
    입력된 query 문자열을 기반으로 상위 5개의 결과를 가져옵니다.
    Args:query (str): 검색할 쿼리 문자열
    Returns:list: 정리된 검색 결과 리스트
    """

    url = "https://api.firecrawl.dev/v2/search"

    payload = {
        "query":query,
        "limit": 5,
        "scrapeOptions": {
            "formats": ["markdown"]
        },
    }

    headers = {
        "Authorization": f"Bearer {os.getenv('FIRECRAWL_API_KEY')}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)
    response = response.json()
    

    if not response["success"] :
        return "Error using tool."

    cleaned_chunks = []

    for result in response.get("data", {}).get("web", []):

        title = result.get("title", "")
        url = result.get("url", "")
        markdown = result.get("markdown", "")

        cleaned = re.sub(r"\\+|\n+", "", markdown).strip()
        cleaned = re.sub(r"\[[^\]]+\]\([^\)]+\)|https?://[^\s]+", "", cleaned)

        cleaned_result = {
            "title": title,
            "url": url,
            "markdown": cleaned,
        }

        cleaned_chunks.append(cleaned_result)

    return cleaned_chunks
    

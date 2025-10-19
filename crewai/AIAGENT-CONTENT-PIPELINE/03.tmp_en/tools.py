import os, re
import requests
from crewai.tools import tool


@tool
def web_search_tool(query: str):
    """
    Web Search Tool.
    Args:
        query: str
            The query to search the web for.
    Returns
        A list of search results with the website content in Markdown format.
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
    

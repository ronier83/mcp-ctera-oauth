from mcp.server.fastmcp import FastMCP
from tavily import TavilyClient
from typing import Dict, List
import os
from dotenv import load_dotenv

load_dotenv()

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
if not TAVILY_API_KEY:
    raise ValueError("TAVILY_API_KEY environment variable not set")

# Create an MCP server
mcp = FastMCP("web-search")

# Initialize Tavily client
tavily_client = TavilyClient(TAVILY_API_KEY)

# Add a tool that uses Tavily
@mcp.tool()
def web_search(query: str) -> List[Dict]:
    """
    Use this tool to search the web for information.

    Args:
        query: The search query.

    Returns:
        The search results.
    """
    try:
        response = tavily_client.search(query)
        return response["results"]
    except Exception as e:
        return "Error: " + str(e)


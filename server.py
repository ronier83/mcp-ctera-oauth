from mcp.server.fastmcp import FastMCP
from tavily import TavilyClient
from dotenv import load_dotenv
from typing import Dict, List
import os

import contextlib
from fastapi import FastAPI, HTTPException, Depends, Request
# import httpx
# from typing import Optional
# import jwt

load_dotenv()

# # OAuth Configuration - Replace with your actual Scalekit configuration
# SCALEKIT_ENVIRONMENT_URL = os.environ.get("SCALEKIT_ENVIRONMENT_URL", "https://your-org.scalekit.com")
# RESOURCE_IDENTIFIER = os.environ.get("RESOURCE_IDENTIFIER", "https://your-mcp-server.com")

if "TAVILY_API_KEY" not in os.environ:
    raise Exception("TAVILY_API_KEY environment variable not set")
  
# Tavily API key
TAVILY_API_KEY = os.environ["TAVILY_API_KEY"]

# # Security scheme for Bearer token
# security = HTTPBearer()

# # Token validation function
# async def validate_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
#     """
#     Validate the OAuth 2.1 access token with Scalekit authorization server
#     """
#     token = credentials.credentials
    
#     try:
#         # In production, you should validate the token with Scalekit's introspection endpoint
#         # or verify the JWT signature if using JWT tokens
#         async with httpx.AsyncClient() as client:
#             response = await client.post(
#                 f"{SCALEKIT_ENVIRONMENT_URL}/oauth/introspect",
#                 data={"token": token},
#                 headers={"Content-Type": "application/x-www-form-urlencoded"}
#             )
            
#             if response.status_code != 200:
#                 raise HTTPException(status_code=401, detail="Invalid token")
            
#             token_info = response.json()
            
#             if not token_info.get("active", False):
#                 raise HTTPException(status_code=401, detail="Token is not active")
            
#             # Verify the audience (resource identifier)
#             if token_info.get("aud") != RESOURCE_IDENTIFIER:
#                 raise HTTPException(status_code=403, detail="Token not valid for this resource")
            
#             return token_info
            
#     except httpx.RequestError:
#         raise HTTPException(status_code=503, detail="Unable to validate token")
#     except Exception as e:
#         raise HTTPException(status_code=401, detail="Token validation failed")

# Initialize Tavily client
tavily_client = TavilyClient(TAVILY_API_KEY)

PORT = os.environ.get("PORT", 10000)

# Create an MCP server
mcp = FastMCP("web-search", host="0.0.0.0", port=PORT)

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

# Create a combined lifespan to manage both session managers
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())
        yield

# Mount the App
app = FastAPI(lifespan=lifespan)
app.mount("/web-search", mcp.streamable_http_app())

# Run the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)

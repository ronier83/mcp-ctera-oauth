from dotenv import load_dotenv
import os
from tavily_mcp import mcp as tavily_mcp_server

import contextlib
from fastapi import FastAPI, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import httpx
from utils import validate_token

################################################################################
# CONFIGURATION 

load_dotenv()

# # OAuth Configuration - Replace with your actual Scalekit configuration
SCALEKIT_ENVIRONMENT_URL = os.environ.get("SCALEKIT_ENVIRONMENT_URL", "")
RESOURCE_IDENTIFIER = os.environ.get("RESOURCE_IDENTIFIER", "")


if not SCALEKIT_ENVIRONMENT_URL:
    raise Exception("SCALEKIT_ENVIRONMENT_URL environment variable not set")
if not RESOURCE_IDENTIFIER:
    raise Exception("RESOURCE_IDENTIFIER environment variable not set")

PORT = os.environ.get("PORT", 10000)

# Create a combined lifespan to manage both session managers
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(tavily_mcp_server.session_manager.run())
        yield

# Mount the App
app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your actual origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

################################################################################
# MCP WELL-KNOWN ENDPOINTS

@app.get("/.well-known/oauth-protected-resource/web-search")
async def oauth_protected_resource_metadata():
    """
    OAuth 2.0 Protected Resource Metadata endpoint for MCP client discovery
    """
    return {
        "authorization_servers": [SCALEKIT_ENVIRONMENT_URL],
        "bearer_methods_supported": ["header"],
        "resource": RESOURCE_IDENTIFIER,
        "resource_documentation": f"{RESOURCE_IDENTIFIER}docs",
        "scopes_supported": []
    }

# Optional: Proxy authorization server metadata for legacy clients
@app.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server_metadata():
    """
    Proxy the authorization server metadata from Scalekit
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SCALEKIT_ENVIRONMENT_URL}/.well-known/oauth-authorization-server"
            )
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=500, detail="Failed to fetch authorization server metadata")
    except httpx.RequestError:
        raise HTTPException(status_code=500, detail="Failed to fetch authorization server metadata")


################################################################################
# MCP SERVER WITH AUTHENTICATION

mcp_server = tavily_mcp_server.streamable_http_app()

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip authentication for metadata endpoints
        if request.url.path.startswith("/.well-known/"):
            return await call_next(request)
        
        # Validate token for MCP endpoints
        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
            
            token = auth_header.split(" ")[1]
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
            await validate_token(credentials)
            
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=401, detail="Authentication failed")
        
        return await call_next(request)

mcp_server.add_middleware(AuthMiddleware)

app.mount("/web-search", mcp_server)

# Run the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)

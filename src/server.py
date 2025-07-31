import contextlib
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import AuthMiddleware
from .config import settings
from .tavily_mcp import mcp as tavily_mcp_server

# Create a combined lifespan to manage the MCP session manager
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    async with tavily_mcp_server.session_manager.run():
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

# MCP well-known endpoint
@app.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource_metadata():
    """
    OAuth 2.0 Protected Resource Metadata endpoint for MCP client discovery.
    Required by the MCP specification for authorization server discovery.
    """
    return {
        "authorization_servers": [f"{settings.SCALEKIT_ENVIRONMENT_URL}/resources/{settings.RESOURCE_IDENTIFIER}"],
        "bearer_methods_supported": ["header"],
        "resource": f"{settings.SCALEKIT_RESOURCE_IDENTIFIER}",
        "resource_documentation": f"{settings.SCALEKIT_RESOURCE_DOCS_URL}/docs",
        "scopes_supported": [],
    }

# Create and mount the MCP server with authentication
mcp_server = tavily_mcp_server.streamable_http_app()
mcp_server.add_middleware(AuthMiddleware)
app.mount("/", mcp_server)

# Run the server
if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=settings.PORT, log_level="debug")

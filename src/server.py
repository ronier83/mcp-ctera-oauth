
import contextlib
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import AuthMiddleware
from .config import settings
from .ctera_mcp import mcp as ctera_mcp_server  # CTERA Portal tools with OAuth protection
import json

# Create a combined lifespan to manage the MCP session manager
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    async with ctera_mcp_server.session_manager.run():
        yield

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
@app.get("/.well-known/oauth-protected-resource/mcp")
async def oauth_protected_resource_metadata():
    """
    OAuth 2.0 Protected Resource Metadata endpoint for MCP client discovery.
    Required by the MCP specification for authorization server discovery.
    """
    response = json.loads(settings.METADATA_JSON_RESPONSE)
    return response

# OAuth Authorization Server Discovery (required by MCP Inspector)
@app.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server_metadata():
    """
    OAuth Authorization Server Metadata endpoint.
    Provides Scalekit authorization server configuration for MCP clients.
    """
    return {
        "issuer": settings.SCALEKIT_ENVIRONMENT_URL,
        "authorization_endpoint": f"{settings.SCALEKIT_ENVIRONMENT_URL}/oauth/authorize",
        "token_endpoint": f"{settings.SCALEKIT_ENVIRONMENT_URL}/oauth/token",
        "jwks_uri": f"{settings.SCALEKIT_ENVIRONMENT_URL}/keys",
        "scopes_supported": ["ctera:read", "ctera:admin", "user:read"],
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "code_challenge_methods_supported": ["S256"],
        "client_id": settings.SCALEKIT_CLIENT_ID,
    }

# Create and mount the MCP server with authentication
mcp_server = ctera_mcp_server.streamable_http_app()
app.add_middleware(AuthMiddleware)
app.mount("/", mcp_server)

def main():
    """Main entry point for the MCP server."""
    uvicorn.run(app, host="localhost", port=settings.PORT, log_level="debug")

if __name__ == "__main__":
    main()

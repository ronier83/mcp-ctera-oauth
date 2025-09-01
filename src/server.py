
import contextlib
import uvicorn
import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from auth import AuthMiddleware
from config import settings
from ctera_mcp import mcp as ctera_mcp_server  # CTERA Portal tools with OAuth protection
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

# OAuth Authorization Server Discovery (what Cursor is looking for)
@app.get("/.well-known/oauth-authorization-server")
@app.get("/.well-known/oauth-authorization-server/mcp")
async def oauth_authorization_server_metadata():
    """
    OAuth Authorization Server Metadata endpoint.
    Provides Scalekit authorization server configuration for MCP clients.
    """
    return {
        "issuer": settings.SCALEKIT_ENVIRONMENT_URL,
        "authorization_endpoint": f"{settings.SCALEKIT_ENVIRONMENT_URL}/oauth/authorize",
        "token_endpoint": f"{settings.SCALEKIT_ENVIRONMENT_URL}/oauth/token", 
        "jwks_uri": f"{settings.SCALEKIT_ENVIRONMENT_URL}/.well-known/jwks",
        "scopes_supported": ["ctera:read", "ctera:admin", "user:read"],
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "code_challenge_methods_supported": ["S256"],
        "client_id": settings.SCALEKIT_CLIENT_ID,
        "registration_endpoint": f"{settings.SCALEKIT_ENVIRONMENT_URL}/oauth/register"
    }

# OpenID Connect Discovery (alternative endpoint Cursor might use)
@app.get("/.well-known/openid-configuration")
@app.get("/.well-known/openid-configuration/mcp")
async def openid_configuration():
    """
    OpenID Connect Discovery endpoint.
    Alternative discovery method for OAuth clients.
    """
    return {
        "issuer": settings.SCALEKIT_ENVIRONMENT_URL,
        "authorization_endpoint": f"{settings.SCALEKIT_ENVIRONMENT_URL}/oauth/authorize",
        "token_endpoint": f"{settings.SCALEKIT_ENVIRONMENT_URL}/oauth/token",
        "userinfo_endpoint": f"{settings.SCALEKIT_ENVIRONMENT_URL}/oauth/userinfo",
        "jwks_uri": f"{settings.SCALEKIT_ENVIRONMENT_URL}/.well-known/jwks",
        "scopes_supported": ["openid", "profile", "email", "ctera:read", "ctera:admin", "user:read"],
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "code_challenge_methods_supported": ["S256"],
        "subject_types_supported": ["public"]
    }

# Client Registration Endpoint (proxy to Scalekit)
@app.post("/register")
async def client_registration(request: Request):
    """
    OAuth Dynamic Client Registration endpoint.
    Proxies registration requests to Scalekit.
    """
    # Get the request body
    body = await request.body()
    
    # Proxy to Scalekit's registration endpoint
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.SCALEKIT_ENVIRONMENT_URL}/oauth/register",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.SCALEKIT_CLIENT_SECRET}"
                }
            )
            return response.json()
        except Exception as e:
            return {"error": "registration_failed", "error_description": str(e)}

# Root endpoint - redirect to MCP endpoint
@app.get("/")
async def root():
    """Root endpoint providing basic server information."""
    return {
        "name": "OAuth-Protected CTERA MCP Server",
        "version": "1.0.0",
        "mcp_endpoint": "/mcp",
        "oauth_discovery": "/.well-known/oauth-protected-resource/mcp",
        "authorization_server": "/.well-known/oauth-authorization-server"
    }

# Create and mount the MCP server with authentication
mcp_server = ctera_mcp_server.streamable_http_app()
app.add_middleware(AuthMiddleware)
app.mount("/mcp", mcp_server)

def main():
    """Main entry point for the MCP server."""
    uvicorn.run(app, host="localhost", port=settings.PORT, log_level="debug")

if __name__ == "__main__":
    main()

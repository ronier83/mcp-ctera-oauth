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

PORT = int(os.environ.get("PORT", 10000))

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

@app.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource_metadata():
    """
    OAuth 2.0 Protected Resource Metadata endpoint for MCP client discovery
    Required by MCP specification for authorization server discovery
    """
    return {
        "authorization_servers": [SCALEKIT_ENVIRONMENT_URL],
        "bearer_methods_supported": ["header"],
        "resource": RESOURCE_IDENTIFIER,
        "resource_documentation": f"{RESOURCE_IDENTIFIER}docs",
        "scopes_supported": []
        # "scopes_supported": ["web-search:read", "web-search:write"]
    }

# # Proxy authorization server metadata from Scalekit
# @app.get("/.well-known/oauth-authorization-server")
# async def oauth_authorization_server_metadata():
#     """
#     Proxy the authorization server metadata from Scalekit
#     This allows clients to discover OAuth endpoints and capabilities
#     """
#     try:
#         async with httpx.AsyncClient() as client:
#             response = await client.get(
#                 f"{SCALEKIT_ENVIRONMENT_URL}/.well-known/oauth-authorization-server"
#             )
#             if response.status_code == 200:
#                 return response.json()
#             else:
#                 raise HTTPException(status_code=500, detail="Failed to fetch authorization server metadata")
#     except httpx.RequestError:
#         raise HTTPException(status_code=500, detail="Failed to fetch authorization server metadata")

# # Dynamic Client Registration endpoint
# @app.post("/oauth/register")
# async def dynamic_client_registration(request: Request):
#     """
#     Dynamic Client Registration endpoint
#     Proxies registration requests to Scalekit authorization server
#     """
#     try:
#         body = await request.body()
#         async with httpx.AsyncClient() as client:
#             response = await client.post(
#                 f"{SCALEKIT_ENVIRONMENT_URL}/oauth/register",
#                 content=body,
#                 headers={
#                     "Content-Type": request.headers.get("Content-Type", "application/json")
#                 }
#             )
            
#             if response.status_code in [200, 201]:
#                 return response.json()
#             else:
#                 raise HTTPException(
#                     status_code=response.status_code, 
#                     detail=f"Client registration failed: {response.text}"
#                 )
#     except httpx.RequestError as e:
#         raise HTTPException(status_code=503, detail=f"Unable to reach authorization server: {str(e)}")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


################################################################################
# MCP SERVER WITH AUTHENTICATION

mcp_server = tavily_mcp_server.streamable_http_app()

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        from fastapi.responses import JSONResponse
        
        # Skip authentication for metadata endpoints and OAuth endpoints
        if (request.url.path.startswith("/.well-known/") or 
            request.url.path.startswith("/oauth/")):
            return await call_next(request)
        
        # Validate token for MCP endpoints
        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                # Return 401 with WWW-Authenticate header as required by MCP spec
                return JSONResponse(
                    status_code=401,
                    content={"error": "unauthorized", "error_description": "Missing or invalid authorization header"},
                    headers={
                        "WWW-Authenticate": f'Bearer realm="OAuth", resource_metadata="{RESOURCE_IDENTIFIER}.well-known/oauth-protected-resource"'
                    }
                )
            
            token = auth_header.split(" ")[1]
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
            await validate_token(credentials)
            
        except HTTPException as e:
            # Return 401/403 with proper WWW-Authenticate header
            return JSONResponse(
                status_code=e.status_code,
                content={"error": "unauthorized" if e.status_code == 401 else "forbidden", "error_description": e.detail},
                headers={
                    "WWW-Authenticate": f'Bearer realm="OAuth", resource_metadata="{RESOURCE_IDENTIFIER}/.well-known/oauth-protected-resource"'
                }
            )
        except Exception as e:
            # Return 401 with WWW-Authenticate header for any other auth failure
            return JSONResponse(
                status_code=401,
                content={"error": "unauthorized", "error_description": "Authentication failed"},
                headers={
                    "WWW-Authenticate": f'Bearer realm="OAuth", resource_metadata="{RESOURCE_IDENTIFIER}/.well-known/oauth-protected-resource"'
                }
            )
        
        return await call_next(request)

mcp_server.add_middleware(AuthMiddleware)

app.mount("/", mcp_server)

# Run the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=PORT)

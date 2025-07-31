import json
import logging
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from scalekit import ScalekitClient
from starlette.middleware.base import BaseHTTPMiddleware
import base64
from typing import List

from .config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Security scheme for Bearer token
security = HTTPBearer()

# Initialize ScaleKit client
scalekit_client = ScalekitClient(
    settings.SCALEKIT_ENVIRONMENT_URL,
    settings.SCALEKIT_CLIENT_ID,
    settings.SCALEKIT_CLIENT_SECRET
)

def extract_scopes(token: str) -> List[str]:
    """
    Extract scopes from a JWT token.
    """
    try:
        token_parts = token.split('.')
        if len(token_parts) != 3:
            raise ValueError("Invalid JWT format")

        payload = json.loads(base64.b64decode(token_parts[1] + '=' * (-len(token_parts[1]) % 4)).decode('utf-8'))
        return payload.get('scopes', [])
    except Exception as e:
        logger.error(f"Failed to extract scopes from token: {e}")
        raise HTTPException(status_code=401, detail="Invalid JWT payload")

# Authentication middleware
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/.well-known/"):
            return await call_next(request)

        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

            token = auth_header.split(" ")[1]
            logger.info(f"Received token: {token}")

            request_body = await request.body()
            validate_options = {}
            
            # Parse JSON from bytes
            try:
                request_data = json.loads(request_body.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                request_data = {}
            
            is_tool_call = request_data.get("method") == "tools/call"
            if is_tool_call:
                required_scopes = ["mcp:tools:search:error"]

                # verify scopes manually on MCP side
                if not all(scope in extract_scopes(token) for scope in required_scopes):
                    raise HTTPException(status_code=403, detail="Your account does not have the required scopes to call this tool.")
                
                validate_options = {"required_scopes": required_scopes}
            
            try:
                scalekit_client.validate_access_token_and_get_claims(
                    token,
                    audience=settings.SCALEKIT_AUDIENCE_NAME,
                    options=validate_options # is this doing anything?
                )
                
            except Exception as e:
                logger.error(f"Token validation failed: {e}")
                raise HTTPException(status_code=401, detail="Token validation failed")

        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={"error": "unauthorized" if e.status_code == 401 else "forbidden", "error_description": e.detail},
                headers={
                    "WWW-Authenticate": f'Bearer realm="OAuth", resource_metadata="{settings.SCALEKIT_RESOURCE_METADATA_URL}"'
                }
            )

        return await call_next(request)
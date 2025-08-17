import json
import logging
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from scalekit import ScalekitClient
from scalekit.common.scalekit import TokenValidationOptions
from starlette.middleware.base import BaseHTTPMiddleware
import jwt
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

def extract_from_token(token: str, key: str) -> str:
    """
    Extract data from a JWT token using PyJWT without signature verification.
    """
    try:
        # Decode JWT payload without signature verification
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload.get(key, [])
    except Exception as e:
        logger.error(f"Failed to extract {key} from token: {e}")
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

            request_body = await request.body()
            
            # Parse JSON from bytes
            try:
                request_data = json.loads(request_body.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                request_data = {}
            
            validation_options = TokenValidationOptions(
              issuer=settings.SCALEKIT_ENVIRONMENT_URL,
              audience=[settings.SCALEKIT_AUDIENCE_NAME],
            )
            
            is_tool_call = request_data.get("method") == "tools/call"
            
            required_scopes = []
            if is_tool_call:
                required_scopes = ["mcp:tools:search:read"] # get required scope for your tool
                
                validation_options.required_scopes = required_scopes
                
                # # verify scopes manually on MCP side
                # if not all(scope in extract_from_token(token, "scopes") for scope in required_scopes):
                #     raise HTTPException(status_code=403, detail="Your account does not have the required scopes")
                  
            
            try:
                # debug start
                logger.info("Validating token...")
                logger.info(f"Required issuer: {validation_options.issuer}")
                logger.info(f"Token issuer: {extract_from_token(token, 'iss')}")
                logger.info(f'Should pass issuer: {"✅" if validation_options.issuer == extract_from_token(token, "iss") else "❌"}')
                
                logger.info(f"Required audience: {validation_options.audience}")
                logger.info(f"Token audience: {extract_from_token(token, 'aud')}")
                logger.info(f'Should pass audience: {"✅" if validation_options.audience == extract_from_token(token, "aud") else "❌"}')
                
                scope_in_token = extract_from_token(token, 'scopes')
                logger.info(f"Required scopes: {required_scopes}")
                logger.info(f"Token scopes: {scope_in_token}")
                logger.info(f'Should pass scopes: {"✅" if all(scope in scope_in_token for scope in required_scopes) else "❌"}')
                # debug end
                
                scalekit_client.validate_access_token(token, options=validation_options)
                
                # debug
                logger.info("✅ Token validation passed")
                
            except Exception as e:
                logger.error(f"❌ Token validation failed: {e}")
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
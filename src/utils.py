import os
import logging
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from scalekit import ScalekitClient

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Security scheme for Bearer token
security = HTTPBearer()

# Get environment variables
SCALEKIT_ENVIRONMENT_URL = os.environ.get("SCALEKIT_ENVIRONMENT_URL", "")
RESOURCE_IDENTIFIER = os.environ.get("RESOURCE_IDENTIFIER", "")
CLIENT_ID = os.environ.get("CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", "")

# Token validation function
async def validate_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Validate the OAuth 2.1 access token with Scalekit authorization server
    """
    token = credentials.credentials
    
    # Debug: Log environment variables (mask sensitive data)
    logger.debug(f"SCALEKIT_ENVIRONMENT_URL: {SCALEKIT_ENVIRONMENT_URL}")
    logger.debug(f"RESOURCE_IDENTIFIER: {RESOURCE_IDENTIFIER}")
    logger.debug(f"CLIENT_ID: {CLIENT_ID[:8]}..." if CLIENT_ID else "CLIENT_ID: None")
    logger.debug(f"CLIENT_SECRET: {'***' if CLIENT_SECRET else 'None'}")
    
    # Debug: Log token info (mask most of the token for security)
    logger.debug(f"Received token: {token[:10]}...{token[-10:]}" if len(token) > 20 else f"Received token: {token}")
    
    try:
        # Debug: Log client initialization attempt
        logger.debug("Initializing Scalekit client...")
        
        # Initialize Scalekit client
        sc = ScalekitClient(
            "https://alejandroao.scalekit.dev",
            CLIENT_ID,
            CLIENT_SECRET
        )
        
        logger.debug("Scalekit client initialized successfully")
        
        # Debug: Log token validation attempt
        logger.debug("Attempting to validate token with Scalekit...")
        
        # Validate the token using Scalekit SDK
        token_info = sc.validate_access_token(token)
        
        # Debug: Log token validation response
        logger.debug(f"Token validation response: {token_info}")
        
        if not token_info:
            logger.error("Token validation returned None/empty response")
            raise HTTPException(status_code=401, detail="Token validation returned empty response")
        
        if not token_info.get("active", False):
            logger.error(f"Token is not active. Token info: {token_info}")
            raise HTTPException(status_code=401, detail="Token is not active")
        
        logger.debug(f"Token is active. Checking audience...")
        
        # Verify the audience (resource identifier)
        token_aud = token_info.get("aud")
        logger.debug(f"Token audience: {token_aud}, Expected: {RESOURCE_IDENTIFIER}")
        
        if token_aud != RESOURCE_IDENTIFIER:
            logger.error(f"Audience mismatch. Token aud: {token_aud}, Expected: {RESOURCE_IDENTIFIER}")
            raise HTTPException(status_code=403, detail=f"Token not valid for this resource. Expected: {RESOURCE_IDENTIFIER}, Got: {token_aud}")
        
        logger.debug("Token validation successful")
        return token_info
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Token validation failed with exception: {type(e).__name__}: {str(e)}")
        logger.exception("Full exception details:")
        raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}")

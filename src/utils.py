import os
import logging
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from scalekit import ScalekitClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Security scheme for Bearer token
security = HTTPBearer()

# Get environment variables
SCALEKIT_ENVIRONMENT_URL = os.environ.get("SCALEKIT_ENVIRONMENT_URL", "")
RESOURCE_IDENTIFIER = os.environ.get("RESOURCE_IDENTIFIER", "")
CLIENT_ID = os.environ.get("CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", "")

# Initialize ScaleKit client
scalekit_client = ScalekitClient(
    "https://alejandroao.scalekit.dev",
    CLIENT_ID,
    CLIENT_SECRET
)

# Token validation function using OAuth introspect endpoint
async def validate_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Validate the OAuth 2.1 access token using the ScaleKit SDK
    """
    token = credentials.credentials
    
    # Validate required environment variables
    if not SCALEKIT_ENVIRONMENT_URL:
        raise HTTPException(status_code=500, detail="Server configuration error: SCALEKIT_ENVIRONMENT_URL not set")
    
    if not CLIENT_ID or not CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Server configuration error: OAuth credentials not configured")
    
    try:
        # Use ScaleKit SDK to introspect the token
        token_info = await scalekit_client.validate_access_token(
          token,
          audience=RESOURCE_IDENTIFIER
        )
        
        # Validate token is active
        is_active = token_info.get("active", False)
        
        if not is_active:
            raise HTTPException(status_code=401, detail="Token is not active")
        
        # Check audience if present
        token_aud = token_info.get("aud")
        
        if token_aud and token_aud != RESOURCE_IDENTIFIER:
            raise HTTPException(
                status_code=403, 
                detail=f"Token not valid for this resource. Expected: {RESOURCE_IDENTIFIER}, Got: {token_aud}"
            )
        
        return token_info
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}")

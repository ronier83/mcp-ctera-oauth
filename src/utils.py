import os
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from scalekit import ScalekitClient

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
    
    try:
        # Initialize Scalekit client
        sc = ScalekitClient(
            SCALEKIT_ENVIRONMENT_URL,
            CLIENT_ID,
            CLIENT_SECRET
        )
        
        # Validate the token using Scalekit SDK
        token_info = await sc.validate_access_token(token)
        
        if not token_info or not token_info.get("active", False):
            raise HTTPException(status_code=401, detail="Token is not active")
        
        # Verify the audience (resource identifier)
        if token_info.get("aud") != RESOURCE_IDENTIFIER:
            raise HTTPException(status_code=403, detail="Token not valid for this resource")
        
        return token_info
        
    except Exception as e:
        raise HTTPException(status_code=401, detail="Token validation failed")

import os
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx

# Security scheme for Bearer token
security = HTTPBearer()

# Get environment variables
SCALEKIT_ENVIRONMENT_URL = os.environ.get("SCALEKIT_ENVIRONMENT_URL", "")
RESOURCE_IDENTIFIER = os.environ.get("RESOURCE_IDENTIFIER", "")

# Token validation function
async def validate_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Validate the OAuth 2.1 access token with Scalekit authorization server
    """
    token = credentials.credentials
    
    try:
        # Validate the token with Scalekit's introspection endpoint
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SCALEKIT_ENVIRONMENT_URL}/oauth/introspect",
                data={"token": token},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            token_info = response.json()
            
            if not token_info.get("active", False):
                raise HTTPException(status_code=401, detail="Token is not active")
            
            # Verify the audience (resource identifier)
            if token_info.get("aud") != RESOURCE_IDENTIFIER:
                raise HTTPException(status_code=403, detail="Token not valid for this resource")
            
            return token_info
            
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Unable to validate token")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Token validation failed")

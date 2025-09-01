# OAuth End-to-End Authentication with CTERA Portal

This document outlines how to implement OAuth 2.1 authentication end-to-end, eliminating the need to store CTERA credentials in your MCP server.

## Current Architecture vs. Proposed Architecture

### Current (Two-Layer Authentication)
```
[MCP Client] --OAuth Token--> [MCP Server] --CTERA Creds--> [CTERA Portal]
```
- Client authenticates via OAuth to access MCP server
- MCP server uses stored CTERA username/password to access CTERA Portal
- Requires storing CTERA credentials in environment variables

### Proposed (End-to-End OAuth)
```
[MCP Client] --OAuth Token--> [MCP Server] --Same OAuth Token--> [CTERA Portal]
```
- Client authenticates via OAuth to access MCP server
- MCP server passes through the same OAuth token to CTERA Portal
- No stored credentials needed - true single sign-on

## Prerequisites

### 1. Check CTERA Portal OAuth Support

**Research Questions:**
- Does your CTERA Portal version support OAuth 2.1/OIDC authentication?
- Can CTERA Portal be configured to trust external identity providers?
- Does CTERA API accept Bearer tokens instead of username/password?

**Where to Check:**
1. **CTERA Documentation** - Look for "OAuth", "OIDC", "SSO", or "Identity Provider" sections
2. **CTERA Admin Panel** - Check authentication configuration options
3. **CTERA API Documentation** - Look for Bearer token authentication examples
4. **CTERA Support** - Contact support to confirm OAuth 2.1 capabilities

### 2. Configure CTERA to Trust Scalekit

If CTERA supports OAuth, you'll need to:

1. **Configure CTERA as an OAuth Resource Server**
   - Set Scalekit as a trusted authorization server
   - Configure audience validation for your CTERA instance

2. **Update Scalekit Configuration**
   - Add CTERA Portal as an additional audience in your OAuth tokens
   - Configure scopes that map to CTERA permissions

## Implementation Steps

### Step 1: Verify CTERA OAuth Capabilities

**Test API Access with OAuth:**
```bash
# Test if CTERA API accepts Bearer tokens
curl -X GET https://your-ctera-portal.com/api/currentSession \
  -H "Authorization: Bearer YOUR_OAUTH_TOKEN"
```

**Expected Response:**
- If OAuth is supported: Valid session information
- If not supported: Authentication error or redirect to login

### Step 2: Update OAuth Token Configuration

**Modify Scalekit Configuration:**
```json
{
  "audience": [
    "http://localhost:10000/mcp",           // Your MCP server
    "https://your-ctera-portal.com/api"    // CTERA Portal API
  ],
  "scopes": [
    "mcp:read", "mcp:write",               // MCP server access
    "ctera:read", "ctera:write", "ctera:admin"  // CTERA Portal access
  ]
}
```

### Step 3: Modify MCP Server Code

**Update Authentication Middleware** (`src/auth.py`):
```python
# Add token to request context for use by CTERA tools
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/.well-known/"):
            return await call_next(request)

        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

            token = auth_header.split(" ")[1]
            
            # Validate token with Scalekit
            validation_options = TokenValidationOptions(
                issuer=settings.SCALEKIT_ENVIRONMENT_URL,
                audience=[settings.SCALEKIT_AUDIENCE_NAME, settings.CTERA_AUDIENCE],  // Multi-audience
            )
            
            scalekit_client.validate_token(token, options=validation_options)
            
            # Add token to request context for CTERA tools
            request.state.oauth_token = token
            
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={"error": "unauthorized", "error_description": e.detail},
                headers={
                    "WWW-Authenticate": f'Bearer realm="OAuth", resource_metadata="{settings.SCALEKIT_RESOURCE_METADATA_URL}"'
                }
            )

        return await call_next(request)
```

**Update CTERA MCP Tools** (`src/ctera_mcp.py`):
```python
# Remove username/password authentication, use OAuth token instead
@dataclass
class PortalContext:
    def __init__(self, host: str, oauth_token: str):
        self.host = host
        self.oauth_token = oauth_token
        # Initialize CTERA client with OAuth token instead of credentials

    async def api_call(self, endpoint: str, method: str = "GET", data: dict = None):
        """Make authenticated API call to CTERA using OAuth token."""
        headers = {
            "Authorization": f"Bearer {self.oauth_token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=f"https://{self.host}/api{endpoint}",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            return response.json()

# Updated lifespan manager
@asynccontextmanager
async def ctera_lifespan(mcp: FastMCP) -> AsyncIterator[PortalContext]:   
    # OAuth token will be provided per-request, not in lifespan
    yield None  # No global session needed

# Updated tools to accept OAuth token from request context
@mcp.tool()
async def ctera_portal_who_am_i(ctx: Context) -> str:
    """Get information about the currently authenticated user."""
    oauth_token = ctx.request_context.request.state.oauth_token
    
    portal = PortalContext(
        host=settings.CTERA_HOST,
        oauth_token=oauth_token
    )
    
    session = await portal.api_call('/currentSession')
    username = session['username']
    if session.get('domain'):
        username = f"{username}@{session['domain']}"

    return f'Authenticated as {username}'

@mcp.tool()
async def ctera_portal_list_dir(
    path: str, 
    ctx: Context,
    include_deleted: bool = False
) -> List[Dict]:
    """List the contents of a directory in the CTERA Portal."""
    oauth_token = ctx.request_context.request.state.oauth_token
    
    portal = PortalContext(
        host=settings.CTERA_HOST,
        oauth_token=oauth_token
    )
    
    # Make OAuth-authenticated API call to list directory
    response = await portal.api_call(f'/files/browse?path={path}&includeDeleted={include_deleted}')
    
    return [{
        'name': f['name'],
        'last_modified': f['lastModified'],
        'deleted': f.get('isDeleted', False),
        'is_dir': f['isFolder'],
        'id': f.get('id')
    } for f in response.get('items', [])]
```

**Update Configuration** (`src/config.py`):
```python
class Settings:
    # Existing Scalekit configuration...
    
    # CTERA OAuth Configuration (replace username/password config)
    CTERA_HOST: str = os.environ.get("CTERA_HOST", "")
    CTERA_AUDIENCE: str = os.environ.get("CTERA_AUDIENCE", "")  # OAuth audience for CTERA
    
    def __post_init__(self):
        # Remove CTERA username/password validation
        # Add CTERA OAuth validation
        if not self.CTERA_HOST:
            raise ValueError("CTERA_HOST environment variable not set")
        if not self.CTERA_AUDIENCE:
            raise ValueError("CTERA_AUDIENCE environment variable not set")
```

**Update Environment Variables** (`.env`):
```env
# Remove these CTERA credential variables:
# ctera.mcp.core.settings.scope=user
# ctera.mcp.core.settings.user=user1
# ctera.mcp.core.settings.password=password1!
# ctera.mcp.core.settings.ssl=false

# Add these OAuth variables:
CTERA_HOST=192.168.94.137
CTERA_AUDIENCE=https://192.168.94.137/api

# Update Scalekit metadata to include CTERA audience:
METADATA_JSON_RESPONSE={"authorization_servers":["https://ziltoid.scalekit.dev/resources/res_88327625704997908"],"bearer_methods_supported":["header"],"resource":"http://localhost:10000/mcp","resource_documentation":"http://localhost:10000/mcp/docs","scopes_supported":["user:read","ctera:read","ctera:admin"],"additional_audiences":["https://192.168.94.137/api"]}
```

## Testing OAuth End-to-End Flow

### 1. Test CTERA OAuth API Access
```bash
# Get OAuth token from Scalekit (implement OAuth client flow)
TOKEN="your_oauth_access_token"

# Test direct CTERA API access with OAuth token
curl -X GET https://192.168.94.137/api/currentSession \
  -H "Authorization: Bearer $TOKEN"
```

### 2. Test MCP Server with OAuth Token
```bash
# Test MCP tool with OAuth token
curl -X POST http://localhost:10000/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "ctera_portal_who_am_i",
      "arguments": {}
    }
  }'
```

## Benefits of OAuth End-to-End

### Security Benefits
- ✅ **No stored credentials** - eliminates credential theft risk
- ✅ **User-specific access** - each user's OAuth token provides their own CTERA access
- ✅ **Token expiration** - automatic session management via OAuth token lifecycle
- ✅ **Audit trail** - all CTERA access tied to specific OAuth tokens/users

### Operational Benefits  
- ✅ **Single sign-on** - users authenticate once for both MCP and CTERA access
- ✅ **Simplified deployment** - no credential management in server configuration
- ✅ **Better compliance** - follows OAuth 2.1 security best practices
- ✅ **Scalability** - supports multiple users without shared service accounts

## Considerations and Limitations

### Requirements
- CTERA Portal must support OAuth 2.1/OIDC authentication
- CTERA must trust Scalekit as an authorization server
- OAuth tokens must include appropriate audiences and scopes

### Fallback Strategy
If CTERA doesn't support OAuth:
- Keep current username/password approach as fallback
- Consider CTERA API token authentication if available
- Implement user-provided credentials (pass CTERA creds as tool parameters)

## Implementation Checklist

- [ ] Research CTERA Portal OAuth 2.1 support
- [ ] Test CTERA API with Bearer token authentication
- [ ] Configure CTERA to trust Scalekit authorization server
- [ ] Update Scalekit configuration for multi-audience tokens
- [ ] Modify MCP server authentication middleware
- [ ] Update CTERA tools to use OAuth tokens
- [ ] Update environment configuration
- [ ] Test end-to-end OAuth flow
- [ ] Document OAuth client implementation for MCP clients

## Next Steps

1. **Research Phase**: Determine if your CTERA Portal supports OAuth 2.1
2. **Proof of Concept**: Test direct OAuth authentication with CTERA API
3. **Implementation**: Follow the code changes outlined above
4. **Testing**: Validate end-to-end OAuth flow
5. **Documentation**: Update README with OAuth client flow examples

---

**Note**: This approach eliminates the need for stored CTERA credentials and provides true end-to-end OAuth security. The implementation depends on CTERA Portal's OAuth capabilities - verify support before proceeding with the code changes.

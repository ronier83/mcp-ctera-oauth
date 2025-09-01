# OAuth-Protected CTERA MCP Server

This is a secure Model Context Protocol (MCP) server that implements OAuth 2.1 authentication using Scalekit as the authorization server. The server provides CTERA Portal management capabilities with enterprise-grade security, ensuring proper authentication and authorization for all CTERA operations.

## What is MCP?

MCP (Model Context Protocol) is a protocol designed for communication between LLMs and tools or resources. This implementation adds enterprise-grade security through OAuth 2.1 authentication, making it suitable for production deployments where access control is critical.

![MCP](./docs/mcp-client-server.png)

## Features

- **OAuth 2.1 Authentication**: Secure access using Scalekit authorization server
- **MCP Compliance**: Implements the MCP authorization specification
- **CTERA Portal Management**: Provides secure CTERA Portal operations and file management
- **Session Management**: Automatic CTERA session handling with refresh capabilities
- **Token Validation**: Validates access tokens with proper audience checking
- **Security Best Practices**: Implements PKCE, proper error handling, and token audience validation 

## Prerequisites

1. **Scalekit Account**: Sign up at [Scalekit](https://app.scalekit.com/ws/signup)
2. **CTERA Portal**: Access to a CTERA Portal instance with valid user credentials
3. **Python 3.11+**: Required for running the server

## Setup

### 1. Install Dependencies

```bash
pip install -e .
```

### 2. Configure Environment Variables

Copy the example environment file and configure your settings:

```bash
cp .env.example .env
```

Edit `.env` with your actual values:

```env
# Scalekit OAuth Configuration
SCALEKIT_ENVIRONMENT_URL=https://your-company.scalekit.com
SCALEKIT_CLIENT_ID=your_scalekit_client_id
SCALEKIT_CLIENT_SECRET=your_scalekit_client_secret
SCALEKIT_RESOURCE_METADATA_URL=https://your-company.scalekit.com/resources/your_resource_id/.well-known/oauth-protected-resource
SCALEKIT_AUDIENCE_NAME=your_resource_id
METADATA_JSON_RESPONSE={"authorization_servers":["https://your-company.scalekit.com/resources/your_resource_id"],"bearer_methods_supported":["header"],"resource":"http://localhost:10000/mcp","scopes_supported":["ctera:read","ctera:admin","user:read"]}

# CTERA Portal Configuration
ctera.mcp.core.settings.scope=admin
ctera.mcp.core.settings.host=your-ctera-portal.com
ctera.mcp.core.settings.user=your_ctera_username
ctera.mcp.core.settings.password=your_ctera_password
ctera.mcp.core.settings.port=443
ctera.mcp.core.settings.ssl=true

# Server Configuration
PORT=10000
```

### 3. Configure Scalekit

In the Scalekit dashboard:

1. Navigate to **MCP servers** and click **Add MCP server**
2. Configure your server:
   - **Server name**: "CTERA Portal MCP Server"
   - **Resource identifier**: Your server URL (e.g., `http://localhost:10000/mcp`)
   - **Allow dynamic client registration**: Enable this
   - **Access token lifetime**: 300-3600 seconds
   - **Scopes**: `ctera:read`, `ctera:admin`, `user:read`

## Running the Server

```bash
python src/server.py
```

The server will start on `http://localhost:10000` (or your configured port).

## API Endpoints

### OAuth Discovery Endpoints

- `GET /.well-known/oauth-protected-resource/mcp` - Resource metadata for MCP client discovery

### MCP Endpoints

- `POST /` - Main MCP endpoint (requires authentication)

## Available CTERA Tools

The following tools are available through the MCP interface:

1. **`ctera_portal_who_am_i`** - Get information about the currently authenticated CTERA user
2. **`ctera_portal_list_dir`** - List contents of a directory in CTERA Portal
3. **`ctera_portal_browse_team_portal`** - Browse to a specific Team Portal tenant (admin only)
4. **`ctera_portal_browse_global_admin`** - Browse to global administration scope

## Authentication Flow

1. **Discovery**: MCP client discovers authorization server via `/.well-known/oauth-protected-resource`
2. **Registration**: Client registers with authorization server (if using dynamic registration)
3. **Authorization**: User authorizes the client through OAuth 2.1 flow
4. **Token Usage**: Client includes access token in `Authorization: Bearer <token>` header
5. **Validation**: Server validates token with Scalekit and checks audience

## Error Handling

The server returns proper HTTP status codes and WWW-Authenticate headers:

- `401 Unauthorized`: Missing or invalid token
- `403 Forbidden`: Valid token but insufficient permissions
- `503 Service Unavailable`: Unable to validate token with authorization server

## Security Features

- **Token Audience Validation**: Ensures tokens are issued specifically for this server
- **PKCE Support**: Protects against authorization code interception
- **Proper Error Responses**: Returns WWW-Authenticate headers as required by MCP spec
- **Scope-based Authorization**: Controls access to specific functionality

## Troubleshooting

### Common Issues

1. **Client Registration Fails**
   - Check that `SCALEKIT_ENVIRONMENT_URL` is correct
   - Ensure dynamic client registration is enabled in Scalekit dashboard
   - Verify network connectivity to Scalekit

2. **Token Validation Fails**
   - Check that `RESOURCE_IDENTIFIER` matches what's configured in Scalekit
   - Ensure the token was issued for the correct audience
   - Verify token hasn't expired

3. **CTERA Portal Connection Fails**
   - Check that CTERA Portal configuration variables are set correctly
   - Verify CTERA Portal host is accessible and credentials are valid
   - Ensure CTERA Portal supports the configured authentication scope (admin/user)

### Debug Mode

For debugging, you can add logging to see detailed error messages:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Project Structure

```
src/
├── server.py          # Main FastAPI server with OAuth middleware
├── ctera_mcp.py       # MCP server implementation with CTERA Portal integration
├── auth.py            # OAuth authentication middleware
├── config.py          # Configuration and environment variable management
└── __init__.py        # Package initialization

oauth-ctera.md         # Guide for OAuth end-to-end implementation
```

## Key Implementation Details

This implementation provides enterprise-grade security for CTERA Portal management:

1. **OAuth 2.1 Security**:
   - Complete OAuth 2.1 authentication using Scalekit authorization server
   - Proper WWW-Authenticate headers as required by MCP specification
   - Token validation with audience checking for enhanced security

2. **CTERA Portal Integration**:
   - Secure session management with automatic refresh handling
   - Support for both admin and user scopes
   - Four production-ready CTERA Portal management tools
   - Configurable SSL/non-SSL connections

3. **Enterprise Features**:
   - MCP-compliant error responses and discovery endpoints
   - Comprehensive logging and debugging capabilities
   - Environment-based configuration management
   - Production-ready error handling

4. **Security Best Practices**:
   - Implements OAuth 2.1 security standards
   - Validates tokens with proper audience checking
   - Secure credential management for CTERA Portal access
   - Proper scope-based authorization

## OAuth End-to-End Enhancement

For even greater security, see `oauth-ctera.md` for implementing OAuth authentication end-to-end, eliminating the need to store CTERA credentials in your server configuration.

The server is fully compliant with the MCP authorization specification and ready for production deployment with enterprise-grade security.
import os
import logging
import functools
from dataclasses import dataclass
from contextlib import asynccontextmanager
from typing import AsyncIterator, Callable, Dict, List
from mcp.server.fastmcp import FastMCP, Context
from cterasdk import AsyncGlobalAdmin, AsyncServicesPortal, settings, exceptions


logger = logging.getLogger('ctera.mcp.core')
logger.setLevel(logging.INFO)
logger.info("Starting CTERA Portal Model Context Protocol [MCP] Server.")


@dataclass
class Env:
    """Environment configuration for CTERA Portal connection."""

    __namespace__ = 'ctera.mcp.core.settings'

    def __init__(self, scope, host, user, password):
        self.scope = scope
        self.host = host
        self.user = user
        self.password = password
        self.port = os.environ.get(f'{Env.__namespace__}.port', 443)
        ssl = os.environ.get(f'{Env.__namespace__}.ssl', None)
        self.ssl = False if ssl in ['false', 'False', False] else True

    @staticmethod
    def load():
        scope = os.environ.get(f'{Env.__namespace__}.scope', None)
        host = os.environ.get(f'{Env.__namespace__}.host', None)
        user = os.environ.get(f'{Env.__namespace__}.user', None)
        password = os.environ.get(f'{Env.__namespace__}.password', None)
        return Env(scope, host, user, password)


@dataclass
class PortalContext:
    """Context manager for CTERA Portal session management."""

    def __init__(self, core, env: Env):
        settings.core.asyn.settings.connector.ssl = env.ssl
        self._session = core(env.host, env.port)
        self._user = env.user
        self._password = env.password

    @property
    def session(self):
        return self._session

    async def login(self):
        """Login to CTERA Portal."""
        await self.session.login(self._user, self._password)

    async def logout(self):
        """Logout from CTERA Portal."""
        await self.session.logout()

    @staticmethod  
    def initialize(env: Env):
        """Initialize Portal Context based on scope."""
        if env.scope == 'admin':
            return PortalContext(AsyncGlobalAdmin, env)
        elif env.scope == 'user':
            return PortalContext(AsyncServicesPortal, env)
        else:
            raise ValueError(f'Scope error: value must be "admin" or "user": {env.scope}')


@asynccontextmanager
async def ctera_lifespan(mcp: FastMCP) -> AsyncIterator[PortalContext]:   
    """Lifespan manager for CTERA Portal session."""
    env = Env.load()
    user = PortalContext.initialize(env)
    try:
        await user.login()
        yield user
    finally:
        await user.logout()


# Create an MCP server for CTERA Portal management with OAuth protection
mcp = FastMCP("ctera-portal", lifespan=ctera_lifespan)


def with_session_refresh(function: Callable) -> Callable:
    """
    Decorator to handle session expiration and automatic refresh.

    Args:
        function: The function to wrap with session refresh logic

    Returns:
        Wrapped function that handles session refresh
    """
    @functools.wraps(function)
    async def wrapper(*args, **kwargs):
        ctx = kwargs.get('ctx')
        user = ctx.request_context.lifespan_context.session
        try:
            return await function(*args, **kwargs)
        except exceptions.session.SessionExpired:
            logger.info("Session expired, refreshing...")
            await user.login()
            return await function(*args, **kwargs)
        except Exception as e:
            logger.error(f'Uncaught exception: {e}')
            raise

    return wrapper


# CTERA Portal MCP Tools
@mcp.tool()
@with_session_refresh
async def ctera_portal_browse_team_portal(
    tenant: str, ctx: Context
) -> str:
    """
    Browse to a specific Team Portal tenant.
    
    Args:
        tenant: The name of the tenant to browse to
        ctx: MCP context for session management
        
    Returns:
        Success message or error if not authorized
        
    Raises:
        Requires global administrator privileges
    """
    user = ctx.request_context.lifespan_context.session
    if user.context != 'admin':
        return (
            'Context error: you must be a global administrator to browse '
            'Team Portal tenants.'
        )
    if user.session().current_tenant() == tenant:
        return (
            f'You are already operating within the scope of the '
            f'"{tenant}" tenant.'
        )
    await user.portals.browse(tenant)
    return f'Changed context to the "{tenant}" tenant.'


@mcp.tool()
@with_session_refresh
async def ctera_portal_browse_global_admin(
    ctx: Context
) -> str:
    """
    Browse to the global administration scope.
    
    Args:
        ctx: MCP context for session management
        
    Returns:
        Success message indicating context change or current state
    """
    user = ctx.request_context.lifespan_context.session
    if not user.session().in_tenant_context():
        return (
            'You are already operating within the global administration '
            'scope.'
        )
    await user.portals.browse_global_admin()
    return 'Changed context to global administration scope.'


@mcp.tool()
@with_session_refresh
async def ctera_portal_who_am_i(ctx: Context) -> str:
    """
    Get information about the currently authenticated user.
    
    Args:
        ctx: MCP context for session management
        
    Returns:
        Username and domain information of authenticated user
    """
    user = ctx.request_context.lifespan_context.session
    session = await user.v1.api.get('/currentSession')
    username = session.username
    if session.domain:
        username = f'{username}@{session.domain}'

    return f'Authenticated as {username}'


@mcp.tool()
@with_session_refresh
async def ctera_portal_list_dir(
    path: str, 
    ctx: Context,
    include_deleted: bool = False
) -> List[Dict]:
    """
    List the contents of a directory in the CTERA Portal.
    
    Args:
        path: Directory path to list
        include_deleted: Whether to include deleted files
        ctx: MCP context for session management
        
    Returns:
        List of dictionaries containing file/folder information
    """
    user = ctx.request_context.lifespan_context.session
    iterator = await user.files.listdir(
        path, include_deleted=include_deleted
    )

    return [{
        'name': f.name,
        'last_modified': f.lastmodified,
        'deleted': f.isDeleted,
        'is_dir': f.isFolder,
        'id': getattr(f, 'fileId', None)
    } async for f in iterator]

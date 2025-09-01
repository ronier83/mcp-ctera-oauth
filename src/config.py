import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # ScaleKit Configuration
    SCALEKIT_ENVIRONMENT_URL: str = os.environ.get("SCALEKIT_ENVIRONMENT_URL", "")
    SCALEKIT_CLIENT_ID: str = os.environ.get("SCALEKIT_CLIENT_ID", "")
    SCALEKIT_CLIENT_SECRET: str = os.environ.get("SCALEKIT_CLIENT_SECRET", "")
    SCALEKIT_RESOURCE_METADATA_URL: str = os.environ.get("SCALEKIT_RESOURCE_METADATA_URL", "")
    SCALEKIT_AUDIENCE_NAME: str = os.environ.get("SCALEKIT_AUDIENCE_NAME", "")
    METADATA_JSON_RESPONSE: str = os.environ.get("METADATA_JSON_RESPONSE", "")

    # CTERA Portal Configuration
    # These environment variables are used by the CTERA SDK
    CTERA_SCOPE: str = os.environ.get("ctera.mcp.core.settings.scope", "")
    CTERA_HOST: str = os.environ.get("ctera.mcp.core.settings.host", "")
    CTERA_USER: str = os.environ.get("ctera.mcp.core.settings.user", "")
    CTERA_PASSWORD: str = os.environ.get("ctera.mcp.core.settings.password", "")
    CTERA_PORT: int = int(os.environ.get("ctera.mcp.core.settings.port", 443))
    CTERA_SSL: str = os.environ.get("ctera.mcp.core.settings.ssl", "true")

    # Server Port
    PORT: int = int(os.environ.get("PORT", 10000))

    def __post_init__(self):
        if not self.SCALEKIT_CLIENT_ID:
            raise ValueError("SCALEKIT_CLIENT_ID environment variable not set")
        if not self.SCALEKIT_CLIENT_SECRET:
            raise ValueError("SCALEKIT_CLIENT_SECRET environment variable not set")
        if not self.SCALEKIT_ENVIRONMENT_URL:
            raise ValueError("SCALEKIT_ENVIRONMENT_URL environment variable not set")
        if not self.SCALEKIT_RESOURCE_METADATA_URL:
            raise ValueError("SCALEKIT_RESOURCE_METADATA_URL environment variable not set")
        if not self.SCALEKIT_AUDIENCE_NAME:
            raise ValueError("SCALEKIT_AUDIENCE_NAME environment variable not set")
        # Validate CTERA Portal configuration
        if not self.CTERA_SCOPE:
            raise ValueError("ctera.mcp.core.settings.scope environment variable not set")
        if not self.CTERA_HOST:
            raise ValueError("ctera.mcp.core.settings.host environment variable not set")
        if not self.CTERA_USER:
            raise ValueError("ctera.mcp.core.settings.user environment variable not set")
        if not self.CTERA_PASSWORD:
            raise ValueError("ctera.mcp.core.settings.password environment variable not set")
        if self.CTERA_SCOPE not in ['admin', 'user']:
            raise ValueError("ctera.mcp.core.settings.scope must be 'admin' or 'user'")

settings = Settings()
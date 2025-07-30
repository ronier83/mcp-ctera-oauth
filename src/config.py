import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # ScaleKit Configuration
    SCALEKIT_ENVIRONMENT_URL: str = os.environ.get("SCALEKIT_ENVIRONMENT_URL", "")
    RESOURCE_IDENTIFIER: str = os.environ.get("RESOURCE_IDENTIFIER", "")
    CLIENT_ID: str = os.environ.get("CLIENT_ID", "")
    CLIENT_SECRET: str = os.environ.get("CLIENT_SECRET", "")

    # Tavily API Key
    TAVILY_API_KEY: str = os.environ.get("TAVILY_API_KEY", "")

    # Server Port
    PORT: int = int(os.environ.get("PORT", 10000))

    def __post_init__(self):
        if not self.SCALEKIT_ENVIRONMENT_URL:
            raise ValueError("SCALEKIT_ENVIRONMENT_URL environment variable not set")
        if not self.RESOURCE_IDENTIFIER:
            raise ValueError("RESOURCE_IDENTIFIER environment variable not set")
        if not self.CLIENT_ID or not self.CLIENT_SECRET:
            raise ValueError("OAuth credentials (CLIENT_ID, CLIENT_SECRET) not configured")
        if not self.TAVILY_API_KEY:
            raise ValueError("TAVILY_API_KEY environment variable not set")

settings = Settings()
"""Configuration management for CamouSolverr."""

import os
from typing import Optional


class Config:
    """Application configuration loaded from environment variables."""

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info").upper()
    LOG_HTML: bool = os.getenv("LOG_HTML", "false").lower() == "true"

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8191"))

    # Browser
    HEADLESS: bool = os.getenv("HEADLESS", "true").lower() == "true"
    TEST_URL: str = os.getenv("TEST_URL", "https://www.google.com")

    # Proxy (global defaults)
    PROXY_URL: Optional[str] = os.getenv("PROXY_URL")
    PROXY_USERNAME: Optional[str] = os.getenv("PROXY_USERNAME")
    PROXY_PASSWORD: Optional[str] = os.getenv("PROXY_PASSWORD")

    # Internationalization
    TZ: str = os.getenv("TZ", "UTC")
    LANG: Optional[str] = os.getenv("LANG")

    # Application metadata
    VERSION: str = "1.0.0"

    @classmethod
    def get_proxy_config(cls) -> Optional[dict]:
        """Get proxy configuration as a dict for Camoufox."""
        if not cls.PROXY_URL:
            return None

        config = {"server": cls.PROXY_URL}
        if cls.PROXY_USERNAME:
            config["username"] = cls.PROXY_USERNAME
        if cls.PROXY_PASSWORD:
            config["password"] = cls.PROXY_PASSWORD

        return config


config = Config()

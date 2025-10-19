"""Main FastAPI application entry point."""

import signal
import sys
from contextlib import asynccontextmanager
from typing import cast

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from playwright.async_api import Browser

from src.browser import session_manager
from src.config import config
from src.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    logger.info(f"Starting CamouSolverr v{config.VERSION}")
    logger.info(f"Log level: {config.LOG_LEVEL}")
    logger.info(f"Headless mode: {config.HEADLESS}")
    logger.info(f"Test URL: {config.TEST_URL}")

    # Test browser installation
    try:
        from camoufox import AsyncCamoufox

        logger.info("Testing Camoufox installation...")
        async with AsyncCamoufox(headless=True) as browser_raw:
            browser = cast(Browser, browser_raw)
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(config.TEST_URL, timeout=30000)
            title = await page.title()
            logger.info(f"Browser test successful! Page title: {title}")
            await page.close()
            await context.close()
    except Exception as e:
        logger.error(f"Browser test failed: {e}")
        logger.warning("CamouSolverr may not function correctly")

    yield

    # Shutdown event
    logger.info("Shutting down CamouSolverr...")
    await session_manager.close_all()
    logger.info("All sessions closed. Goodbye!")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="CamouSolverr",
        description=("FlareSolverr-compatible proxy server using Camoufox"),
        version=config.VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routes
    app.include_router(router)

    return app


def handle_shutdown(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)


def main():
    """Main entry point."""
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    # Create app
    app = create_app()

    # Run server
    logger.info(f"Starting server on {config.HOST}:{config.PORT}")
    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        log_level=config.LOG_LEVEL.lower(),
        access_log=True,
    )


if __name__ == "__main__":
    main()

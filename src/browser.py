"""Browser and session management with async Camoufox."""

import asyncio
import random
from asyncio import wait_for
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, cast
from uuid import uuid4

from loguru import logger
from playwright.async_api import Browser, BrowserContext, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright_captcha import CaptchaType, ClickSolver, FrameworkType

from camoufox import AsyncCamoufox
from src.config import config
from src.models import CookieModel, ProxyModel

# Challenge detection constants
CHALLENGE_TITLES = [
    "Just a moment...",  # Cloudflare
    "DDoS-Guard",  # DDoS-GUARD
]


class BrowserSession:
    """Represents a persistent browser session with its own context and solver."""

    def __init__(
        self,
        session_id: str,
        browser: Browser,
        context: BrowserContext,
        page: Page,
        solver: ClickSolver,
        camoufox_instance: AsyncCamoufox,
        proxy: Optional[ProxyModel] = None,
        ttl: Optional[timedelta] = None,
    ):
        self.session_id = session_id
        self.browser = browser
        self.context = context
        self.page = page
        self.solver = solver
        self.camoufox_instance = camoufox_instance
        self.proxy = proxy
        self.ttl = ttl
        self.created_at = datetime.now()
        self.last_used = datetime.now()

    def update_last_used(self) -> None:
        """Update the last used timestamp."""
        self.last_used = datetime.now()

    def lifetime(self) -> timedelta:
        """Get the lifetime of the session."""
        return datetime.now() - self.created_at

    def is_expired(self) -> bool:
        """Check if the session has expired based on its TTL."""
        if self.ttl is None:
            return False
        return self.lifetime() > self.ttl

    async def close(self) -> None:
        """Close the browser session."""
        try:
            # Close page and context first
            await self.page.close()
            await self.context.close()
            # Properly exit the Camoufox context manager
            await self.camoufox_instance.__aexit__(None, None, None)
            logger.info(f"Session {self.session_id} closed successfully")
        except Exception as e:
            logger.error(f"Error closing session {self.session_id}: {e}")


class SessionManager:
    """Manages browser sessions."""

    def __init__(self):
        self._sessions: Dict[str, BrowserSession] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_interval = 10  # Check for expired sessions every 10 seconds

    async def create_session(
        self,
        session_id: Optional[str] = None,
        proxy: Optional[ProxyModel] = None,
        ttl: Optional[timedelta] = None,
    ) -> Tuple[BrowserSession, bool]:
        """
        Create a new browser session.

        Returns:
            Tuple of (session, is_new) where is_new indicates if a new session was created
        """
        async with self._lock:
            # Generate session ID if not provided
            if session_id is None:
                session_id = str(uuid4())

            # Check if session already exists
            if session_id in self._sessions:
                existing_session = self._sessions[session_id]
                existing_session.update_last_used()
                logger.info(f"Returning existing session: {session_id}")
                return existing_session, False

            # Create new browser and context
            logger.info(f"Creating new browser session: {session_id}")

            # Configure proxy
            proxy_config = None
            if proxy:
                proxy_config = {"server": proxy.url}
                if proxy.username:
                    proxy_config["username"] = proxy.username
                if proxy.password:
                    proxy_config["password"] = proxy.password
            elif config.get_proxy_config():
                proxy_config = config.get_proxy_config()

            # Launch Camoufox
            try:
                camoufox = await AsyncCamoufox(
                    headless=config.HEADLESS,
                    proxy=proxy_config,
                    humanize=True,
                    geoip=True,
                ).__aenter__()
            except Exception:
                # Fallback without geoip if not installed
                camoufox = await AsyncCamoufox(
                    headless=config.HEADLESS,
                    proxy=proxy_config,
                    humanize=True,
                ).__aenter__()

            browser = cast(Browser, camoufox)

            # Create context and page
            viewport_width = random.randint(1280, 1920)
            viewport_height = random.randint(720, 1080)
            context = await browser.new_context(
                viewport={"width": viewport_width, "height": viewport_height}
            )
            page = await context.new_page()

            # Create solver
            solver = await ClickSolver(
                framework=FrameworkType.CAMOUFOX,
                page=page,
                max_attempts=10,
                attempt_delay=1,
            ).__aenter__()

            # Create session object
            session = BrowserSession(
                session_id=session_id,
                browser=browser,
                context=context,
                page=page,
                solver=solver,
                camoufox_instance=camoufox,
                proxy=proxy,
                ttl=ttl,
            )

            self._sessions[session_id] = session
            logger.info(f"Session {session_id} created successfully")
            return session, True

    async def get_session(
        self, session_id: str, ttl: Optional[timedelta] = None
    ) -> Tuple[BrowserSession, bool]:
        """
        Get an existing session or create a new one.

        Args:
            session_id: Session ID
            ttl: Time-to-live for session rotation

        Returns:
            Tuple of (session, is_new)
        """
        async with self._lock:
            if session_id in self._sessions:
                session = self._sessions[session_id]

                # Check if session has expired based on its stored TTL
                if session.is_expired():
                    logger.info(
                        f"Session {session_id} expired (TTL: {session.ttl}), rotating..."
                    )
                    await session.close()
                    del self._sessions[session_id]
                    # Create new session with same ID and TTL
                    return await self.create_session(
                        session_id=session_id, proxy=session.proxy, ttl=session.ttl
                    )

                session.update_last_used()
                return session, False

        # Session doesn't exist, create it with specified TTL
        return await self.create_session(session_id=session_id, ttl=ttl)

    async def destroy_session(self, session_id: str) -> bool:
        """
        Destroy a session.

        Returns:
            True if session existed and was destroyed, False otherwise
        """
        async with self._lock:
            if session_id in self._sessions:
                session = self._sessions[session_id]
                await session.close()
                del self._sessions[session_id]
                logger.info(f"Session {session_id} destroyed")
                return True
            return False

    def list_sessions(self) -> list[str]:
        """List all active session IDs."""
        return list(self._sessions.keys())

    async def _cleanup_expired_sessions(self) -> None:
        """Remove expired sessions based on their TTL."""
        async with self._lock:
            expired_sessions = [
                session_id
                for session_id, session in self._sessions.items()
                if session.is_expired()
            ]

            for session_id in expired_sessions:
                session = self._sessions[session_id]
                logger.info(
                    f"Cleaning up expired session: {session_id} (TTL: {session.ttl})"
                )
                await session.close()
                del self._sessions[session_id]

            if expired_sessions:
                logger.info(f"Cleaned up {len(expired_sessions)} expired session(s)")

    async def _cleanup_loop(self) -> None:
        """Background loop to periodically clean up expired sessions."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                # logger.info("Cleaning up expired sessions...")
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                logger.info("Cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    def start_cleanup(self) -> None:
        """Start the background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Started background session cleanup task")

    async def stop_cleanup(self) -> None:
        """Stop the background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped background session cleanup task")

    async def close_all(self) -> None:
        """Close all sessions (cleanup)."""
        await self.stop_cleanup()
        async with self._lock:
            for session in self._sessions.values():
                await session.close()
            self._sessions.clear()
            logger.info("All sessions closed")


# Global session manager
session_manager = SessionManager()


async def resolve_challenge(
    page: Page,
    solver: ClickSolver,
    url: str,
    method: str = "GET",
    post_data: Optional[str] = None,
    cookies: Optional[list[CookieModel]] = None,
    wait_seconds: Optional[int] = None,
    max_timeout: int = 60000,
) -> dict:
    """
    Navigate to URL and resolve any Cloudflare challenges.

    Args:
        page: Playwright page
        solver: Captcha solver
        url: Target URL
        method: HTTP method (GET or POST)
        post_data: POST data (if method is POST)
        cookies: Cookies to set before navigation
        wait_seconds: Additional wait time after solving
        max_timeout: Maximum timeout in milliseconds

    Returns:
        Dictionary with solution data
    """
    timeout_seconds = max_timeout / 1000

    # Add random mouse movement
    await page.mouse.move(random.randint(50, 200), random.randint(50, 200))
    await page.wait_for_timeout(random.randint(100, 300))

    # Navigate to page
    logger.debug(f"Navigating to {url} using {method}")

    # Capture the response to get the actual HTTP status code
    response = None
    if method == "POST" and post_data:
        # Create a form and submit it for POST requests
        html_form = f"""
        <!DOCTYPE html>
        <html>
        <body>
            <form id="postForm" action="{url}" method="POST">
        """
        # Parse post_data (format: key=value&key2=value2)
        if post_data:
            for pair in post_data.split("&"):
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    html_form += f'<input type="hidden" name="{key}" value="{value}">\n'
        html_form += """
            </form>
            <script>document.getElementById('postForm').submit();</script>
        </body>
        </html>
        """
        response = await page.goto(f"data:text/html,{html_form}")
    else:
        response = await page.goto(url, timeout=int(timeout_seconds * 1000))

    # Extract status code from response (default to 200 if not available)
    status_code = response.status if response else 200

    # Set cookies if provided
    if cookies:
        logger.debug("Setting cookies...")
        cookie_dicts = []
        for cookie in cookies:
            cookie_dict: dict = {
                "name": cookie.name,
                "value": cookie.value,
                "domain": cookie.domain or "",
                "path": cookie.path or "/",
                "expires": cookie.expires or -1,
                "httpOnly": cookie.httpOnly or False,
                "secure": cookie.secure or False,
            }
            if cookie.sameSite and cookie.sameSite in ("Lax", "None", "Strict"):
                cookie_dict["sameSite"] = cookie.sameSite  # type: ignore
            cookie_dicts.append(cookie_dict)
        await page.context.add_cookies(cookie_dicts)  # type: ignore
        # Reload with cookies and capture new response status
        if method == "POST" and post_data:
            response = await page.goto(f"data:text/html,{html_form}")
        else:
            response = await page.goto(url, timeout=int(timeout_seconds * 1000))
        # Update status code after reload
        status_code = response.status if response else status_code

    # Wait for page load
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=int(timeout_seconds * 1000))
        await page.wait_for_load_state("networkidle", timeout=int(timeout_seconds * 1000))
    except PlaywrightTimeoutError:
        logger.warning("Timeout waiting for page load states")

    # Log HTML if enabled
    if config.LOG_HTML:
        page_source = await page.content()
        logger.debug(f"Response HTML:\n{page_source}")

    # Check for challenge
    page_title = await page.title()
    challenge_detected = any(title.lower() in page_title.lower() for title in CHALLENGE_TITLES)

    message = "Challenge not detected!"
    if challenge_detected:
        logger.info(f"Challenge detected. Title: {page_title}")
        try:
            # Attempt to solve the challenge
            remaining_timeout = timeout_seconds - 5  # Reserve 5 seconds
            await wait_for(
                solver.solve_captcha(
                    captcha_container=page,
                    captcha_type=CaptchaType.CLOUDFLARE_INTERSTITIAL,
                    wait_checkbox_attempts=1,
                    wait_checkbox_delay=0.5,
                ),
                timeout=remaining_timeout,
            )
            logger.info("Challenge solved successfully!")
            message = "Challenge solved!"
        except asyncio.TimeoutError:
            raise Exception(f"Timeout solving challenge after {timeout_seconds} seconds")
        except Exception as e:
            logger.error(f"Error solving challenge: {e}")
            raise Exception(f"Error solving challenge: {str(e)}")

    # Additional wait if requested
    if wait_seconds and wait_seconds > 0:
        logger.info(f"Waiting {wait_seconds} seconds before returning...")
        await page.wait_for_timeout(wait_seconds * 1000)

    # Get final page data
    final_url = page.url
    page_content = await page.content()
    cookies_result = await page.context.cookies()
    user_agent = await page.evaluate("navigator.userAgent")

    # Convert cookies to our model
    cookie_models = [
        CookieModel(
            name=cookie["name"],
            value=cookie["value"],
            domain=cookie.get("domain"),
            path=cookie.get("path", "/"),
            expires=cookie.get("expires"),
            httpOnly=cookie.get("httpOnly", False),
            secure=cookie.get("secure", False),
            sameSite=cookie.get("sameSite"),
        )
        for cookie in cookies_result
    ]

    return {
        "url": final_url,
        "status": status_code,  # HTTP status code from the response
        "cookies": cookie_models,
        "userAgent": user_agent,
        "response": page_content,
        "message": message,
    }

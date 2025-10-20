"""API routes for CamouSolverr."""

import time
from datetime import timedelta
from typing import cast

from fastapi import APIRouter, HTTPException
from loguru import logger
from playwright.async_api import Browser

from camoufox import AsyncCamoufox
from src.browser import resolve_challenge, session_manager
from src.config import config
from src.logger import get_request_id, reset_request_id, set_request_id
from src.models import (
    HealthResponse,
    IndexResponse,
    SolutionModel,
    V1RequestBase,
    V1ResponseBase,
)

router = APIRouter()


@router.get("/")
async def index() -> IndexResponse:
    """Index endpoint."""
    # Create a temporary browser to get user agent
    async with AsyncCamoufox(headless=True) as browser_raw:
        browser = cast(Browser, browser_raw)
        context = await browser.new_context()
        page = await context.new_page()
        user_agent = await page.evaluate("navigator.userAgent")
        await page.close()
        await context.close()

    return IndexResponse(
        msg="CamouSolverr is ready!",
        version=config.VERSION,
        userAgent=user_agent,
    )


@router.get("/health")
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok")


@router.post("/v1")
async def v1_endpoint(req: V1RequestBase) -> V1ResponseBase:
    """Main V1 endpoint compatible with FlareSolverr."""
    # Generate and set request ID for logging
    request_id = get_request_id()
    set_request_id(request_id)

    start_ts = int(time.time() * 1000)
    logger.info(f"Incoming request => POST /v1 cmd={req.cmd}")

    try:
        # Validate command
        if req.cmd is None:
            raise HTTPException(status_code=400, detail="Request parameter 'cmd' is mandatory.")

        # Set default timeout
        if req.maxTimeout is None or req.maxTimeout < 1:
            req.maxTimeout = 60000

        # Route to appropriate handler
        if req.cmd == "sessions.create":
            res = await cmd_sessions_create(req)
        elif req.cmd == "sessions.list":
            res = await cmd_sessions_list(req)
        elif req.cmd == "sessions.destroy":
            res = await cmd_sessions_destroy(req)
        elif req.cmd == "request.get":
            res = await cmd_request_get(req)
        elif req.cmd == "request.post":
            res = await cmd_request_post(req)
        else:
            raise HTTPException(
                status_code=400, detail=f"Request parameter 'cmd' = '{req.cmd}' is invalid."
            )

        # Add timestamps and version
        res.startTimestamp = start_ts
        res.endTimestamp = int(time.time() * 1000)
        res.version = config.VERSION

        duration = (res.endTimestamp - res.startTimestamp) / 1000
        logger.info(f"Response in {duration} s")

        return res

    except HTTPException as e:
        logger.error(f"Error handling request: {e.detail}")
        res = V1ResponseBase(
            status="error",
            message=f"Error: {e.detail}",
            startTimestamp=start_ts,
            endTimestamp=int(time.time() * 1000),
            version=config.VERSION,
        )
        return res
    except Exception as e:
        logger.error(f"Error handling request: {e}")
        res = V1ResponseBase(
            status="error",
            message=f"Error: {str(e)}",
            startTimestamp=start_ts,
            endTimestamp=int(time.time() * 1000),
            version=config.VERSION,
        )
        return res
    finally:
        reset_request_id()


async def cmd_sessions_create(req: V1RequestBase) -> V1ResponseBase:
    """Create a new browser session."""
    logger.debug("Creating new session...")

    # Extract TTL if provided
    ttl = timedelta(minutes=req.session_ttl_minutes) if req.session_ttl_minutes else None
    session, is_new = await session_manager.create_session(session_id=req.session, proxy=req.proxy, ttl=ttl)

    if not is_new:
        return V1ResponseBase(
            status="ok",
            message="Session already exists.",
            session=session.session_id,
            startTimestamp=0,
            endTimestamp=0,
            version=config.VERSION,
        )

    return V1ResponseBase(
        status="ok",
        message="Session created successfully.",
        session=session.session_id,
        startTimestamp=0,
        endTimestamp=0,
        version=config.VERSION,
    )


async def cmd_sessions_list(req: V1RequestBase) -> V1ResponseBase:
    """List all active sessions."""
    session_ids = session_manager.list_sessions()

    return V1ResponseBase(
        status="ok",
        message="",
        sessions=session_ids,
        startTimestamp=0,
        endTimestamp=0,
        version=config.VERSION,
    )


async def cmd_sessions_destroy(req: V1RequestBase) -> V1ResponseBase:
    """Destroy a session."""
    if not req.session:
        raise HTTPException(status_code=400, detail="Request parameter 'session' is mandatory.")

    # Prevent destroying the default session
    if req.session == "default":
        raise HTTPException(
            status_code=400,
            detail='Cannot destroy the "default" session. It will automatically restart if needed.',
        )

    existed = await session_manager.destroy_session(req.session)

    if not existed:
        raise HTTPException(status_code=404, detail="The session doesn't exist.")

    return V1ResponseBase(
        status="ok",
        message="The session has been removed.",
        startTimestamp=0,
        endTimestamp=0,
        version=config.VERSION,
    )


async def cmd_request_get(req: V1RequestBase) -> V1ResponseBase:
    """Handle GET request with challenge resolution."""
    # Validate
    if not req.url:
        raise HTTPException(
            status_code=400, detail="Request parameter 'url' is mandatory in 'request.get' command."
        )
    if req.postData:
        raise HTTPException(
            status_code=400, detail="Cannot use 'postData' when sending a GET request."
        )

    solution = await handle_request(req, method="GET")

    return V1ResponseBase(
        status="ok",
        message=solution.get("message", ""),
        solution=SolutionModel(
            url=solution["url"],
            status=solution["status"],
            cookies=solution["cookies"] if not req.returnOnlyCookies else solution["cookies"],
            userAgent=solution["userAgent"],
            response=solution.get("response") if not req.returnOnlyCookies else None,
            headers={} if not req.returnOnlyCookies else {},
        ),
        startTimestamp=0,
        endTimestamp=0,
        version=config.VERSION,
    )


async def cmd_request_post(req: V1RequestBase) -> V1ResponseBase:
    """Handle POST request with challenge resolution."""
    # Validate
    if not req.url:
        raise HTTPException(
            status_code=400,
            detail="Request parameter 'url' is mandatory in 'request.post' command.",
        )
    if not req.postData:
        raise HTTPException(
            status_code=400,
            detail="Request parameter 'postData' is mandatory in 'request.post' command.",
        )

    solution = await handle_request(req, method="POST")

    return V1ResponseBase(
        status="ok",
        message=solution.get("message", ""),
        solution=SolutionModel(
            url=solution["url"],
            status=solution["status"],
            cookies=solution["cookies"] if not req.returnOnlyCookies else solution["cookies"],
            userAgent=solution["userAgent"],
            response=solution.get("response") if not req.returnOnlyCookies else None,
            headers={} if not req.returnOnlyCookies else {},
        ),
        startTimestamp=0,
        endTimestamp=0,
        version=config.VERSION,
    )


async def handle_request(req: V1RequestBase, method: str) -> dict:
    """
    Handle request with session (defaults to "default" session).

    Args:
        req: Request object
        method: HTTP method (GET or POST)

    Returns:
        Solution dictionary
    """
    # Use "default" session if no session specified
    session_id = req.session or "default"
    ttl = timedelta(minutes=req.session_ttl_minutes) if req.session_ttl_minutes else None
    session, is_new = await session_manager.get_session(session_id, ttl)

    if is_new:
        logger.debug(f"New session created: {session.session_id}")
    else:
        logger.debug(
            f"Using existing session: {session.session_id} (lifetime={session.lifetime()})"
        )

    # Use session's page and solver
    solution = await resolve_challenge(
        page=session.page,
        solver=session.solver,
        url=req.url or "",
        method=method,
        post_data=req.postData,
        cookies=req.cookies,
        wait_seconds=req.waitInSeconds,
        max_timeout=req.maxTimeout or 60000,
    )
    return solution

"""Pydantic models for CamouSolverr API (strict camelCase)."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CookieModel(BaseModel):
    """Cookie model matching Selenium/Playwright cookie format."""

    name: str
    value: str
    domain: Optional[str] = None
    path: Optional[str] = "/"
    expires: Optional[float] = None
    size: Optional[int] = None
    httpOnly: Optional[bool] = False
    secure: Optional[bool] = False
    session: Optional[bool] = True
    sameSite: Optional[str] = None


class ProxyModel(BaseModel):
    """Proxy configuration model."""

    url: str
    username: Optional[str] = None
    password: Optional[str] = None


class V1RequestBase(BaseModel):
    """Base model for /v1 endpoint requests."""

    model_config = ConfigDict(populate_by_name=True)

    cmd: Optional[str] = None
    url: Optional[str] = None
    maxTimeout: Optional[int] = Field(default=60000, description="Timeout in milliseconds")
    cookies: Optional[List[CookieModel]] = None
    returnOnlyCookies: Optional[bool] = False
    proxy: Optional[ProxyModel] = None
    session: Optional[str] = None
    session_ttl_minutes: Optional[int] = Field(default=None, alias="sessionTtlMinutes")
    postData: Optional[str] = None
    waitInSeconds: Optional[int] = Field(default=None, alias="waitInSeconds")


class SolutionModel(BaseModel):
    """Solution model for successful responses."""

    url: str
    status: int
    headers: Dict[str, Any] = Field(default_factory=dict)
    response: Optional[str] = None
    cookies: List[CookieModel] = Field(default_factory=list)
    userAgent: str


class V1ResponseBase(BaseModel):
    """Base model for /v1 endpoint responses."""

    status: str  # "ok" or "error"
    message: str
    startTimestamp: int
    endTimestamp: int
    version: str
    solution: Optional[SolutionModel] = None
    # For sessions.list
    sessions: Optional[List[str]] = None
    # For sessions.create
    session: Optional[str] = None


class IndexResponse(BaseModel):
    """Response for index endpoint."""

    msg: str
    version: str
    userAgent: str


class HealthResponse(BaseModel):
    """Response for health check endpoint."""

    status: str

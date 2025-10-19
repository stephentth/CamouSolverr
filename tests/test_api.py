import pytest
from fastapi.testclient import TestClient

from src.main import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


def test_index(client):
    """Test index endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["msg"] == "CamouSolverr is ready!"
    assert "version" in data
    assert "userAgent" in data


def test_health(client):
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_v1_sessions_create(client):
    """Test session creation."""
    response = client.post(
        "/v1",
        json={
            "cmd": "sessions.create",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "session" in data
    assert data["message"] == "Session created successfully."


def test_v1_sessions_list(client):
    """Test session listing."""
    # First create a session
    create_resp = client.post(
        "/v1",
        json={
            "cmd": "sessions.create",
            "session": "test-session-1",
        },
    )
    assert create_resp.status_code == 200

    # List sessions
    response = client.post(
        "/v1",
        json={
            "cmd": "sessions.list",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "sessions" in data
    assert "test-session-1" in data["sessions"]


def test_v1_sessions_destroy(client):
    """Test session destruction."""
    # Create a session
    create_resp = client.post(
        "/v1",
        json={
            "cmd": "sessions.create",
            "session": "test-session-2",
        },
    )
    assert create_resp.status_code == 200

    # Destroy the session
    response = client.post(
        "/v1",
        json={
            "cmd": "sessions.destroy",
            "session": "test-session-2",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["message"] == "The session has been removed."


def test_v1_invalid_cmd(client):
    """Test invalid command."""
    response = client.post(
        "/v1",
        json={
            "cmd": "invalid.command",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"


def test_v1_missing_cmd(client):
    """Test missing cmd parameter."""
    response = client.post(
        "/v1",
        json={},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"


def test_v1_request_get_missing_url(client):
    """Test request.get without URL."""
    response = client.post(
        "/v1",
        json={
            "cmd": "request.get",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"


def test_v1_request_post_missing_postdata(client):
    """Test request.post without postData."""
    response = client.post(
        "/v1",
        json={
            "cmd": "request.post",
            "url": "https://example.com",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"

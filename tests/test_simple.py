"""Simple tests for CamouSolverr."""

import time

import httpx
import pytest
from bs4 import BeautifulSoup

BASE_URL = "http://localhost:8191"
# Docs: https://httpbin.dmuth.org/openapi.json
HTTPBIN_URL = "http://httpbin"  # Internal Docker network URL (port 80 is default)


@pytest.mark.timeout(600)  # 10 minutes
def test_default_session_sequential_requests():
    """Test 4 sequential requests using the default session."""
    # httpbin endpoints to test different features
    urls = [
        f"{HTTPBIN_URL}/html",
        f"{HTTPBIN_URL}/get",
        f"{HTTPBIN_URL}/headers",
        f"{HTTPBIN_URL}/user-agent",
    ]

    # Make 4 sequential requests to httpbin in the default session
    for i, url in enumerate(urls):
        response = httpx.post(
            f"{BASE_URL}/v1",
            json={
                "cmd": "request.get",
                "url": url,
                "maxTimeout": 60000,
            },
            timeout=120.0,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["solution"]["status"] == 200
        # httpbin might add trailing slashes, so check if URLs match
        assert url in data["solution"]["url"] or data["solution"]["url"] in url
        print(f"Request {i + 1}/4 completed successfully in default session: {url}")


@pytest.mark.timeout(600)  # 10 minutes
def test_multiple_sessions_and_list():
    """Test creating multiple sessions with requests, then listing them."""
    session_ids = ["session1", "session2", "session3", "session4"]
    urls = [
        f"{HTTPBIN_URL}/html",
        f"{HTTPBIN_URL}/get",
        f"{HTTPBIN_URL}/headers",
        f"{HTTPBIN_URL}/user-agent",
    ]

    # Create 4 different sessions and make a request in each
    for i, (session_id, url) in enumerate(zip(session_ids, urls)):
        # Create session
        create_response = httpx.post(
            f"{BASE_URL}/v1",
            json={
                "cmd": "sessions.create",
                "session": session_id,
            },
            timeout=120.0,
        )
        assert create_response.status_code == 200
        create_data = create_response.json()
        assert create_data["status"] == "ok"
        assert create_data["session"] == session_id

        # Make request in this session
        request_response = httpx.post(
            f"{BASE_URL}/v1",
            json={
                "cmd": "request.get",
                "url": url,
                "session": session_id,
                "maxTimeout": 60000,
            },
            timeout=120.0,
        )
        assert request_response.status_code == 200
        request_data = request_response.json()
        assert request_data["status"] == "ok"
        assert request_data["solution"]["status"] == 200
        # httpbin might add trailing slashes, so check if URLs match
        assert url in request_data["solution"]["url"] or request_data["solution"]["url"] in url
        print(f"Request {i + 1}/4 completed successfully in {session_id}: {url}")

    # Get list of sessions and verify all created sessions are present
    list_response = httpx.post(
        f"{BASE_URL}/v1",
        json={
            "cmd": "sessions.list",
        },
        timeout=30.0,
    )

    assert list_response.status_code == 200
    data = list_response.json()
    assert data["status"] == "ok"
    assert "sessions" in data

    # Verify all created sessions are in the list
    for session_id in session_ids:
        assert session_id in data["sessions"]

    print(f"Sessions list retrieved successfully: {data['sessions']}")


@pytest.mark.timeout(600)  # 10 minutes
def test_session_ttl_expiration():
    """Test that a session with TTL=1 minute expires after 70 seconds."""
    session_id = "ttl_test_session"

    # Create session with TTL of 1 minute
    create_response = httpx.post(
        f"{BASE_URL}/v1",
        json={
            "cmd": "sessions.create",
            "session": session_id,
            "sessionTtlMinutes": 1,  # 1 minute TTL
        },
        timeout=120.0,
    )
    assert create_response.status_code == 200
    create_data = create_response.json()
    assert create_data["status"] == "ok"
    assert create_data["session"] == session_id
    print(f"Created session '{session_id}' with TTL=1 minute")

    # Verify session exists
    list_response = httpx.post(
        f"{BASE_URL}/v1",
        json={"cmd": "sessions.list"},
        timeout=30.0,
    )
    assert list_response.status_code == 200
    list_data = list_response.json()
    assert session_id in list_data["sessions"]
    print(f"Session '{session_id}' confirmed in session list")

    # Wait for 70 seconds (1 minute + 10 second buffer)
    print("Waiting 70 seconds for session to expire...")
    time.sleep(70)

    # Check if session has been removed
    list_response_after = httpx.post(
        f"{BASE_URL}/v1",
        json={"cmd": "sessions.list"},
        timeout=30.0,
    )
    assert list_response_after.status_code == 200
    list_data_after = list_response_after.json()
    assert session_id not in list_data_after["sessions"]
    print(f"Session '{session_id}' successfully removed after TTL expiration")


@pytest.mark.timeout(120)  # 2 minutes
def test_request_with_delay_success():
    """Test that a request with delay within timeout succeeds."""
    # Request with 2 second delay and 10 second timeout (should succeed)
    delay_seconds = 2
    url = f"{HTTPBIN_URL}/delay/{delay_seconds}"

    print(f"Testing request with {delay_seconds}s delay (within timeout)...")
    response = httpx.post(
        f"{BASE_URL}/v1",
        json={
            "cmd": "request.get",
            "url": url,
            "maxTimeout": 10000,  # 10 second timeout
        },
        timeout=20.0,  # httpx client timeout
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["solution"]["status"] == 200
    print(f"Request with {delay_seconds}s delay completed successfully")


@pytest.mark.timeout(120)  # 2 minutes
def test_request_timeout():
    """Test that a request exceeding maxTimeout returns an error."""
    # Request with 10 second delay but only 5 second timeout (should timeout)
    delay_seconds = 10
    url = f"{HTTPBIN_URL}/delay/{delay_seconds}"

    print(f"Testing request with {delay_seconds}s delay (exceeds timeout)...")
    response = httpx.post(
        f"{BASE_URL}/v1",
        json={
            "cmd": "request.get",
            "url": url,
            "maxTimeout": 5000,  # 5 second timeout (less than 10s delay)
        },
        timeout=20.0,  # httpx client timeout
    )

    assert response.status_code == 200
    data = response.json()
    # Should return error status when timeout occurs
    assert data["status"] == "error"
    assert "timeout" in data["message"].lower() or "error" in data["message"].lower()
    print(f"Request correctly timed out: {data['message']}")


@pytest.mark.timeout(120)  # 2 minutes
def test_request_status_500():
    """Test that a request to an endpoint returning 500 status is handled correctly."""
    # Request to /status/500 which returns HTTP 500
    url = f"{HTTPBIN_URL}/status/500"

    print("Testing request to endpoint returning 500 status code...")
    response = httpx.post(
        f"{BASE_URL}/v1",
        json={
            "cmd": "request.get",
            "url": url,
            "maxTimeout": 10000,  # 10 second timeout
        },
        timeout=20.0,  # httpx client timeout
    )

    assert response.status_code == 200
    data = response.json()
    # The proxy should still return ok since it successfully navigated
    # The solution should contain the actual status code from the target
    assert data["status"] == "ok"
    assert data["solution"]["status"] == 500
    print(f"Request completed, received status code: {data['solution']['status']}")


@pytest.mark.timeout(600)  # 10 minutes
def test_wikipedia_random_page_title():
    """Test requesting a random Wikipedia page and parsing the title from HTML."""
    url = "https://en.wikipedia.org/wiki/Special:Random"

    print("Testing request to Wikipedia random page...")
    response = httpx.post(
        f"{BASE_URL}/v1",
        json={
            "cmd": "request.get",
            "url": url,
            "maxTimeout": 60000,  # 60 second timeout
        },
        timeout=120.0,  # httpx client timeout
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["solution"]["status"] == 200

    # Parse the HTML response using BeautifulSoup
    html_content = data["solution"]["response"]
    soup = BeautifulSoup(html_content, "html.parser")

    # Debug: print some info about the page
    print(f"Final URL: {data['solution']['url']}")

    # Wikipedia page titles can be in different structures, try multiple approaches:
    # 1. Try to find span with class "mw-page-title-main" (newer Wikipedia pages)
    title_element = soup.find("span", class_="mw-page-title-main")

    # 2. If not found, try to find h1 with id "firstHeading" (common on Wikipedia)
    if title_element is None:
        h1_title = soup.find("h1", id="firstHeading")
        if h1_title:
            title_element = h1_title

    # 3. If still not found, try any h1 with class containing "firstHeading"
    if title_element is None:
        h1_title = soup.find("h1", class_=lambda x: x and "firstHeading" in x)
        if h1_title:
            title_element = h1_title

    # Assert that we found a title element
    assert title_element is not None, "Could not find Wikipedia page title element"
    page_title = title_element.get_text(strip=True)
    assert len(page_title) > 0, "Page title is empty"

    print(f"Successfully retrieved Wikipedia page: '{page_title}'")

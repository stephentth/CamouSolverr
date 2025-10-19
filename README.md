# CamouSolverr

CamouSolverr is a FlareSolverr-compatible web crawling service using [Camoufox](https://camoufox.com/).

## How it works

CamouSolverr starts a proxy server and waits for user requests in an idle state using few resources.
When a request arrives, it uses Camoufox (a Firefox-based browser) to create a web browser instance. It navigates to the URL with user parameters and returns the HTML content, cookies, and headers.

**NOTE**: Web browsers consume a lot of memory. If you are running CamouSolverr on a machine with limited RAM, do not make many requests at once.

**Important**: By default, CamouSolverr uses a persistent "default" session. This means all requests share the same browser session unless you explicitly specify a different session ID or create temporary sessions. This improves performance and resource usage but means cookies and state are shared across requests.

## Key Features

- **FlareSolverr API Compatible**: Drop-in replacement for FlareSolverr
- **Camoufox Powered**: Uses Camoufox for browser automation
- **Async/Await**: Fully asynchronous implementation for better performance
- **Default Session**: All requests use a persistent "default" session by default
- **Session Management**: Create multiple persistent browser sessions with TTL support
- **Request UUID Logging**: Every request has a unique UUID for easy debugging
- **Strict camelCase API**: JSON API uses strict camelCase (FlareSolverr compatible)

## Differences from FlareSolverr

While CamouSolverr maintains API compatibility with FlareSolverr, there are some key differences:

1. **Browser Engine**: Uses Camoufox (Firefox-based) instead of undetected-chromedriver (Chrome-based)
2. **Implementation**: Fully async Python implementation using FastAPI
3. **Logging**: Enhanced logging with unique request UUIDs for easier debugging
4. **Default Session**: Uses persistent "default" session for all requests by default
5. **Strict camelCase**: JSON API strictly uses camelCase (no snake_case support)

## Installation

### Docker

It is recommended to install using Docker because the project depends on browser binaries that are already included within the image.

```bash
docker run -d \
  --name=camousolverr \
  -p 8191:8191 \
  -e LOG_LEVEL=info \
  --restart unless-stopped \
  camousolverr:latest
```

Or using docker-compose:

```yaml
version: '3.8'

services:
  camousolverr:
    build: .
    container_name: camousolverr
    ports:
      - "8191:8191"
    environment:
      - LOG_LEVEL=info
      - HEADLESS=true
    restart: unless-stopped
    shm_size: 2gb
```

Run with:

```bash
docker-compose up
```

### From source

* Install [Python 3.11+](https://www.python.org/downloads/)
* Install [uv](https://github.com/astral-sh/uv)
* Clone this repository and open a shell in that path
* Run `uv sync` to install dependencies
* Run `uv run python -m src.main` to start CamouSolverr

## Usage

Example request using the default session:
```bash
curl -L -X POST 'http://localhost:8191/v1' \
-H 'Content-Type: application/json' \
--data-raw '{
  "cmd": "request.get",
  "url": "http://www.example.com/",
  "maxTimeout": 60000
}'
```

Example request with a specific session:
```bash
curl -L -X POST 'http://localhost:8191/v1' \
-H 'Content-Type: application/json' \
--data-raw '{
  "cmd": "request.get",
  "url": "http://www.example.com/",
  "session": "my-session-id",
  "maxTimeout": 60000
}'
```

### Commands

#### + `sessions.create`

Create a new browser session with a specific ID.

| Parameter | Notes |
| --- | --- |
| session | Optional. The session ID that you want to be assigned to the instance. If not set, a random UUID will be assigned. |
| proxy | Optional. Eg: `"proxy": {"url": "http://127.0.0.1:8888"}`. You must include the proxy schema in the URL: `http://`, `socks4://` or `socks5://`. Authorization supported. |

```bash
curl -L -X POST 'http://localhost:8191/v1' \
-H 'Content-Type: application/json' \
--data-raw '{
  "cmd": "sessions.create",
  "session": "my-session-id"
}'
```

#### + `sessions.list`

Returns a list of all active sessions.

```bash
curl -L -X POST 'http://localhost:8191/v1' \
-H 'Content-Type: application/json' \
--data-raw '{
  "cmd": "sessions.list"
}'
```

Example response:
```json
{
  "sessions": [
    "default",
    "my-session-id"
  ]
}
```

#### + `sessions.destroy`

Shut down a browser session and free up resources.

| Parameter | Notes |
| --- | --- |
| session | The session ID that you want to be destroyed. |

```bash
curl -L -X POST 'http://localhost:8191/v1' \
-H 'Content-Type: application/json' \
--data-raw '{
  "cmd": "sessions.destroy",
  "session": "my-session-id"
}'
```

**Note**: You cannot destroy the "default" session. It will automatically restart if destroyed.

#### + `request.get`

| Parameter | Notes |
| --- | --- |
| url | Mandatory |
| session | Optional. If not specified, uses the "default" session. Specify a session ID to use a specific session. |
| sessionTtlMinutes | Optional. CamouSolverr will automatically rotate expired sessions based on the TTL provided in minutes. |
| maxTimeout | Optional, default 60000. Max timeout in milliseconds. |
| cookies | Optional. Eg: `"cookies": [{"name": "cookie1", "value": "value1"}]`. |
| returnOnlyCookies | Optional, default false. Only returns the cookies. Response data, headers and other parts of the response are removed. |
| proxy | Optional. Eg: `"proxy": {"url": "http://127.0.0.1:8888"}`. You must include the proxy schema in the URL. Authorization supported. (Ignored when `session` parameter is set.) |
| waitInSeconds | Optional, default none. Length to wait in seconds before returning results. Useful for loading dynamic content. |

```bash
curl -L -X POST 'http://localhost:8191/v1' \
-H 'Content-Type: application/json' \
--data-raw '{
  "cmd": "request.get",
  "url": "http://www.example.com/",
  "maxTimeout": 60000
}'
```

Example response:
```json
{
    "solution": {
        "url": "https://www.example.com/",
        "status": 200,
        "headers": {},
        "response": "<!DOCTYPE html>...",
        "cookies": [
            {
                "name": "session_id",
                "value": "abc123...",
                "domain": ".example.com",
                "path": "/",
                "expires": 1234567890.0,
                "httpOnly": true,
                "secure": true,
                "sameSite": "Lax"
            }
        ],
        "userAgent": "Mozilla/5.0 ..."
    },
    "status": "ok",
    "message": "",
    "startTimestamp": 1234567890123,
    "endTimestamp": 1234567891234,
    "version": "1.0.0"
}
```

### + `request.post`

This is the same as `request.get` but it takes one more parameter:

| Parameter | Notes |
| --- | --- |
| postData | Must be a string with `application/x-www-form-urlencoded`. Eg: `a=b&c=d` |

```bash
curl -L -X POST 'http://localhost:8191/v1' \
-H 'Content-Type: application/json' \
--data-raw '{
  "cmd": "request.post",
  "url": "http://www.example.com/login",
  "postData": "username=user&password=pass",
  "maxTimeout": 60000
}'
```

## Environment variables

| Name | Default | Notes |
| --- | --- | --- |
| LOG_LEVEL | info | Verbosity of the logging. Use `LOG_LEVEL=debug` for more information. |
| LOG_HTML | false | Only for debugging. If `true` all HTML that passes through the proxy will be logged to the console in `debug` level. |
| PROXY_URL | none | URL for proxy. Will be overwritten by `request` or `sessions` proxy if used. Example: `http://127.0.0.1:8080`. |
| PROXY_USERNAME | none | Username for proxy. Example: `testuser`. |
| PROXY_PASSWORD | none | Password for proxy. Example: `testpass`. |
| TZ | UTC | Timezone used in the logs and the web browser. Example: `TZ=Europe/London`. |
| LANG | none | Language used in the web browser. Example: `LANG=en_GB`. |
| HEADLESS | true | Only for debugging. To run the web browser in headless mode or visible. |
| TEST_URL | https://www.google.com | CamouSolverr makes a request on start to make sure the web browser is working. You can change that URL if it is blocked in your country. |
| PORT | 8191 | Listening port. You don't need to change this if you are running on Docker. |
| HOST | 0.0.0.0 | Listening interface. You don't need to change this if you are running on Docker. |

Environment variables are set differently depending on the operating system:
* Docker: Environment variables can be set in the `docker-compose.yml` file or in the Docker CLI command.
* Linux: Run `export LOG_LEVEL=debug` and then run CamouSolverr in the same shell.
* Windows: Open `cmd.exe`, run `set LOG_LEVEL=debug` and then run CamouSolverr in the same shell.

## Development

### Requirements
* Python 3.11+
* uv
* ruff (linter)
* mypy (type checker)

### Setup
```bash
# Clone the repository
git clone https://github.com/yourusername/camousolverr.git
cd camousolverr

# Install dependencies
uv sync --all-extras

# Run linting and type checking
make check

# Run tests
uv run pytest

# Run the server locally
uv run python -m src.main
```

## API Documentation

When running, you can access the interactive API documentation at:
* Swagger UI: http://localhost:8191/docs
* ReDoc: http://localhost:8191/redoc

## Session Behavior

**Important**: CamouSolverr uses a persistent "default" session by default for all requests. This means:

1. **Default Session**: If you don't specify a `session` parameter, your request will use the shared "default" session
2. **Shared State**: All requests using the "default" session share cookies and browser state
3. **Performance**: Using the default session is faster as it doesn't create new browser instances
4. **Explicit Sessions**: To isolate requests, create explicit sessions using `sessions.create` and specify the `session` parameter
5. **Cannot Destroy Default**: The "default" session cannot be permanently destroyed; it will automatically restart

Example of session behavior:
```bash
# Request 1: Uses "default" session (automatically created)
curl -X POST 'http://localhost:8191/v1' \
--data-raw '{"cmd": "request.get", "url": "http://example.com/"}'

# Request 2: Also uses "default" session (shares cookies with Request 1)
curl -X POST 'http://localhost:8191/v1' \
--data-raw '{"cmd": "request.get", "url": "http://example.com/account"}'

# Request 3: Uses isolated session
curl -X POST 'http://localhost:8191/v1' \
--data-raw '{"cmd": "request.get", "url": "http://example.com/", "session": "isolated-session"}'
```

## Troubleshooting

### Browser doesn't start
* Make sure you have enough RAM (minimum 2GB recommended)
* Check that all system dependencies are installed
* Try running with `HEADLESS=false` to see if the browser opens visually

### Issues with requests
* Check logs with `LOG_LEVEL=debug`
* Increase `maxTimeout` value if requests are timing out
* Use explicit session IDs if you need to isolate requests

### Memory issues
* Close unused sessions with `sessions.destroy`
* Avoid making too many concurrent requests
* Increase Docker shared memory with `shm_size: 2gb`

## Credits

* Inspired by [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr)
* Inspired by [Byparr](https://github.com/daijro/byparr)
* Powered by [Camoufox](https://camoufox.com/)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This software is provided for educational, research, and web automation purposes.

**User Responsibility**: Users are solely responsible for their use of this software. You must ensure your use complies with all applicable laws, regulations, and the Terms of Service of any websites you interact with. Always respect website policies, implement appropriate rate limiting, and only automate websites you own or have explicit permission to access.

The developers of this software are not responsible for any misuse or any consequences arising from the use of this software.



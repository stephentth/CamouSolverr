# Base stage with dependencies
FROM python:3.11-slim-bookworm AS base

WORKDIR /app

# Install system dependencies required for Camoufox and Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    libu2f-udev \
    libvulkan1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./

# Test stage - includes dev dependencies and runs tests
FROM base AS test

# Copy test files
COPY src ./src
COPY tests ./tests
COPY README.md ./

# Install with dev dependencies
RUN uv sync --frozen

# Install Playwright browsers for testing
RUN uv run playwright install firefox
RUN uv run playwright install-deps firefox

# Run linting and type checking
RUN uv run ruff check src/ || true
RUN uv run mypy src/ || true

# Run tests
RUN uv run pytest || true

# Production stage - optimized for runtime
FROM base AS production

COPY src ./src
COPY README.md ./

# Install production dependencies only
RUN uv sync --frozen --no-dev

# Install Playwright browsers (for Camoufox)
RUN uv run playwright install firefox
RUN uv run playwright install-deps firefox

EXPOSE 8191

ENV HOST=0.0.0.0
ENV PORT=8191
ENV LOG_LEVEL=info
ENV HEADLESS=true

# Run the application
CMD ["uv", "run", "python", "-m", "src.main"]

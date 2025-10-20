FROM python:3.11-slim-bookworm

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

# Copy dependency files (changes less frequently)
COPY pyproject.toml uv.lock README.md ./

# Install production dependencies only
RUN uv sync --frozen --no-dev

# Pre-download Camoufox browser during build (saves ~707MB download at runtime)
# This is expensive, so we do it before copying src to maximize cache hits
RUN uv run camoufox fetch

# Install Playwright dependencies for browser support
RUN uv run playwright install-deps firefox

# Copy source code (changes frequently, so copied last)
COPY src ./src

EXPOSE 8191

ENV HOST=0.0.0.0
ENV PORT=8191
ENV LOG_LEVEL=info
ENV HEADLESS=true

# Run the application
CMD ["uv", "run", "python", "-m", "src.main"]

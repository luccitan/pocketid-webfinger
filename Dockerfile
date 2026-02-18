# Inspired by
#   https://github.com/astral-sh/uv-docker-example/blob/main/Dockerfile
FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim

RUN groupadd --system --gid 999 nonroot \
 && useradd --system --gid 999 --uid 999 --create-home nonroot

WORKDIR /app

# Multiple UV configurations for productive build
#   1. Enable bytecode
#   2. Copy from cache instead of linking
#   3. No dev dependencies
#   4. Use default bin folder for installed tools
# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_DEV=1
ENV UV_TOOL_BIN_DIR=/usr/local/bin

# Project's custom env. variables
ENV HOST="0.0.0.0"
ENV PORT="8000"

# Install project's dependencies using mounted lockfile and settings
#   then copy project
#   then install the project separately
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked

ENTRYPOINT []
USER nonroot
EXPOSE 8000

HEALTHCHECK --interval=1m --timeout=5s --start-period=5s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:8000/health" || exit 1

CMD ["uv", "run", "main.py"]

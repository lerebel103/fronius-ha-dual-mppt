FROM python:3.14-slim

# Bring in the uv binary from the official image (pinned for reproducibility)
COPY --from=ghcr.io/astral-sh/uv:0.11.28 /uv /uvx /bin/

WORKDIR /app

RUN groupadd -r lerebel103 && useradd -r -g lerebel103 lerebel103

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install runtime dependencies from the lockfile (reproducible, no dev deps),
# using the base image's Python so no second interpreter is downloaded.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_PREFERENCE=only-system
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app/ ./app/

ARG VERSION=dev
RUN printf '"""Version of the Fronius MPPT bridge."""\n\n__version__ = "%s"\n' "${VERSION}" > app/version.py

RUN mkdir -p /etc/fronius-ha-dual-mppt && \
    chown -R lerebel103:lerebel103 /app /etc/fronius-ha-dual-mppt

USER lerebel103

ENV PYTHONPATH=/app \
    PATH="/app/.venv/bin:$PATH"

CMD ["python", "-m", "app", "--config", "/etc/fronius-ha-dual-mppt/config.yaml"]

LABEL maintainer="lerebel103"
LABEL description="Fronius HA Dual MPPT bridge for Home Assistant"
LABEL version="${VERSION}"

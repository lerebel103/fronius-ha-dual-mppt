FROM python:3.14-slim

WORKDIR /app

RUN groupadd -r lerebel103 && useradd -r -g lerebel103 lerebel103

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

ARG VERSION=dev
RUN printf '"""Version of the Fronius MPPT bridge."""\n\n__version__ = "%s"\n' "${VERSION}" > app/version.py

RUN mkdir -p /etc/fronius-ha-dual-mppt && \
    chown -R lerebel103:lerebel103 /app /etc/fronius-ha-dual-mppt

USER lerebel103

ENV PYTHONPATH=/app

CMD ["python", "-m", "app", "--config", "/etc/fronius-ha-dual-mppt/config.yaml"]

LABEL maintainer="lerebel103"
LABEL description="Fronius HA Dual MPPT bridge for Home Assistant"
LABEL version="${VERSION}"

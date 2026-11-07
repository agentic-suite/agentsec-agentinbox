# agentinbox field-test image — the system under test (CLI + dev deps).
#
# Builds from the repo root so it can install the package:
#   docker compose -f scripts/fieldtest/docker-compose.fieldtest.yml build agentinbox
FROM python:3.13-slim

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl procps ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work

# Install agentinbox (CLI + package) with the dev tooling the field suites use.
COPY pyproject.toml README.md LICENSE /work/
COPY agentinbox /work/agentinbox
COPY tests /work/tests
RUN pip install --no-cache-dir -e ".[dev]"

# Field-test home (isolated from the host) and harness mount points.
RUN mkdir -p /data/agentinbox/.agentinbox /ft/scripts /ft/tests
WORKDIR /work

CMD ["sleep", "infinity"]

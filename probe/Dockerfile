# Deterministic reproduction container for neosynaptex-probe.
# Build:  docker build -f probe/Dockerfile -t neosynaptex-probe:0.1.0 .
# Run:    docker run --rm neosynaptex-probe:0.1.0 python probe/reproduce.py
#
# Must produce the same gamma values (6 decimal places) on any host.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONHASHSEED=0 \
    PYTHONPATH=/app/probe/src:/app

WORKDIR /app

# Copy the parent neosynaptex module + its core & contracts, plus probe/.
# We only ship what the probe's reproduce.py actually touches, keeping
# the image slim and the supply chain small.
COPY neosynaptex.py ./neosynaptex.py
COPY core/ ./core/
COPY contracts/ ./contracts/
COPY evidence_bundle_v1/ ./evidence_bundle_v1/
COPY probe/ ./probe/

RUN pip install --no-cache-dir \
        "numpy>=1.26" "scipy>=1.11" \
        "pytest>=8.0" "pytest-timeout>=2.2" \
        "mypy>=1.8" "ruff>=0.4"

# Run reproduce.py by default — any hash divergence is a regression.
CMD ["python", "probe/reproduce.py"]

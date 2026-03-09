# GPU backend: rocm, cuda, cpu
ARG GPU_BACKEND=rocm

# ---------- base ----------
FROM python:3.12-slim AS base

WORKDIR /app

# Install build deps + OpenSSL 3.x with FIPS provider
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    openssl \
    libssl3 \
    && rm -rf /var/lib/apt/lists/*

# Verify OpenSSL 3.x FIPS provider is available
RUN openssl list -providers 2>/dev/null || true && \
    test -f /usr/lib/x86_64-linux-gnu/ossl-modules/fips.so && \
    echo "FIPS provider available" || echo "FIPS provider not found — will use config fallback"

COPY pyproject.toml .
RUN pip install --no-cache-dir .

# ---------- rocm ----------
FROM base AS backend-rocm
RUN pip install --no-cache-dir torch torchvision \
    --index-url https://download.pytorch.org/whl/rocm6.2

# ---------- cuda ----------
FROM base AS backend-cuda
RUN pip install --no-cache-dir torch torchvision \
    --index-url https://download.pytorch.org/whl/cu124

# ---------- cpu ----------
FROM base AS backend-cpu
RUN pip install --no-cache-dir torch torchvision \
    --index-url https://download.pytorch.org/whl/cpu

# ---------- final ----------
FROM backend-${GPU_BACKEND} AS final

# Create non-root user
RUN groupadd -r aiuser && useradd -r -g aiuser -d /app -s /sbin/nologin aiuser && \
    mkdir -p /app/workdir && chown -R aiuser:aiuser /app

COPY --chown=aiuser:aiuser src/ /app/src/
COPY --chown=aiuser:aiuser config/ /app/config/

# FIPS OpenSSL configuration
ENV OPENSSL_CONF=/app/config/openssl-fips.cnf
ENV OPENSSL_MODULES=/usr/lib/x86_64-linux-gnu/ossl-modules

USER aiuser

EXPOSE 8000 3001

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

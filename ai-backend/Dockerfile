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
    libssl-dev \
    libssl3 \
    libffi-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Run fipsinstall to generate the FIPS module config
# This creates fipsmodule.cnf with the HMAC of the FIPS provider .so
RUN if [ -f /usr/lib/x86_64-linux-gnu/ossl-modules/fips.so ]; then \
        openssl fipsinstall \
            -out /etc/ssl/fipsmodule.cnf \
            -module /usr/lib/x86_64-linux-gnu/ossl-modules/fips.so && \
        echo "FIPS provider installed successfully"; \
    else \
        echo "FIPS provider .so not found — FIPS will be best-effort"; \
    fi

# Build cryptography from source against system FIPS OpenSSL
# (pip wheel bundles its own non-FIPS OpenSSL)
COPY pyproject.toml .
RUN pip install --no-cache-dir --no-binary cryptography . && \
    python -c "import ssl; print('SSL version:', ssl.OPENSSL_VERSION)"

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

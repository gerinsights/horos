# GPU backend: rocm, cuda, cpu
ARG GPU_BACKEND=rocm

# ---------- base ----------
FROM python:3.12-slim AS base

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

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

COPY src/ /app/src/
COPY config/ /app/config/

EXPOSE 8000 3001

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

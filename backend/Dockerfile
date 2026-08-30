# TwinVerse Inspect AI — API service
#
# Two dependency layers:
#   requirements.txt            the web service
#   requirements-inference.txt  torch + ultralytics, from the CPU index
#
# The detect endpoints run the model in-process, so inference deps are not
# optional. They are installed from PyTorch's CPU wheel index because the
# default Linux wheels bundle ~2.5 GB of CUDA runtime that a container without
# a GPU can never use.
#
# For GPU inference: drop --extra-index-url below and run with `--gpus all`.

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# libgl1 and libglib2.0-0 are OpenCV's runtime shared libraries. Without them
# `import cv2` fails at startup with a confusing ImportError about libGL.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Requirements first, so dependency layers survive source changes. Inference
# deps are a separate layer: they are far larger and change far less often.
COPY requirements.txt requirements-inference.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements-inference.txt \
        --extra-index-url https://download.pytorch.org/whl/cpu

COPY . .

# Run as a non-root user. A container compromise should not also be root.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

ENV PYTHONPATH=/app

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

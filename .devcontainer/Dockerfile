FROM python:3.11-slim

WORKDIR /workspace

# Install system dependencies for building Python packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*


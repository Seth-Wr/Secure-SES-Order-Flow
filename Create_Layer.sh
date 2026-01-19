#!/usr/bin/env bash

# 1. Clean and create structure
rm -rf python
mkdir -p python

# 2. Install dependencies (Using quotes around pydantic[email] is safer)
pip3 install \
    --platform manylinux2014_aarch64 \
    --target ./python \
    --implementation cp \
    --python-version 3.12 \
    --only-binary=:all: \
    --upgrade \
    fastapi mangum "pydantic[email]" pytz httpx dnspython disposable-email-domains

# 3. CLEANING (Safe way)
# KEEP .dist-info folders for Pydantic!
# Only remove things that are truly useless at runtime:
find python -name "__pycache__" -type d -exec rm -rf {} +
find python -name "tests" -type d -exec rm -rf {} +
find python -name "docs" -type d -exec rm -rf {} +
find python -name "*.pyc" -delete

# 4. Zip it
zip -r9 lambda-fastAPI-layer.zip python

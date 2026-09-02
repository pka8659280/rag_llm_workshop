# =============================================================================
# Docker image for the ABC123 Restaurant RAG web app (FastAPI).
#
# The app itself (WebApps/) is the image content. Qdrant and Ollama run as
# SEPARATE containers orchestrated by docker-compose.yml — they are NOT
# installed inside this image (each has its own official image).
# =============================================================================

# python:3.11-slim: the code uses PEP 604 syntax (str | None) so Python >= 3.10
# is required; 3.11 is a safe, widely available choice. "slim" keeps the image
# small. No apt build tools are needed because every dependency ships wheels.
FROM python:3.11-slim

# Where the app lives inside the container. Uvicorn runs from here so that
# "WebApps.web_app:app" resolves exactly like it does locally (project root).
WORKDIR /app

# 1) Install Python dependencies first.
#    Splitting COPY so a requirements-only change reuses the pip layer cache
#    instead of re-running pip install on every build.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Copy the whole project: chat.py / converter.py / embedding.py (RAG code),
#    WebApps/ (FastAPI app + static pages), spreadsheet_data/ (the Excel data).
#    .dockerignore keeps the build context lean (Guideline/, images/, .git ...).
COPY . .

# Port the FastAPI server listens on.
EXPOSE 8000

# Optional self-check: every 30s hit /docs; 60s grace period for startup.
# If the check fails 3 times in a row Docker marks the container unhealthy.
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/docs')" || exit 1

# --host 0.0.0.0 is REQUIRED: it binds to every interface in the container so
# Docker can forward host traffic to port 8000. (Default is 127.0.0.1 only.)
CMD ["uvicorn", "WebApps.web_app:app", "--host", "0.0.0.0", "--port", "8000"]

# -*- coding: utf-8 -*-
"""
Web UI for the ABC123 Restaurant RAG pipeline — FastAPI.

This file is the app entry point. The routes are split across two files:

  web_app.py      -> app creation + startup (builds the RAG backend once, serves static)
  page_routes.py  -> page routes: GET / (chat.html), GET /reviews (reviews.html)
  api_routes.py   -> JSON APIs: /api/chat, /api/reviews, /api/search

Run with (from the project root):  uvicorn WebApps.web_app:app --port 8000
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles  # serves the /static folder (images, css, ...)

# --- Our own RAG code -----------------------------------------------------------
# chat.py lives in the project root (importable because uvicorn adds the working
# directory to sys.path); page_routes/api_routes live in this same WebApps folder,
# so they are imported as sibling modules of this package.
from chat import COLLECTION_NAME, build  # build() creates the Qdrant store + LLM once
from .page_routes import router as page_router  # HTML pages
from .api_routes import router as api_router    # JSON endpoints

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("web_app")

BASE_DIR = Path(__file__).resolve().parent  # folder that contains web_app.py


# --- Startup ----------------------------------------------------------------------
# build() comes from chat.py; on failure it calls sys.exit(1) (which raises
# SystemExit). We catch it here and keep serving — the /api endpoints then
# return a JSON 500 error with a clear message instead of crashing the server.
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs ONCE when the server starts (and once when it stops)."""
    try:
        # Connect to Qdrant + Ollama and keep them on app.state so every request can use them.
        app.state.store, app.state.llm = build()
        logger.info("RAG backend initialized (collection=%s).", COLLECTION_NAME)
    except (Exception, SystemExit) as e:
        # Backend down? Store "None" so endpoints can reply with a friendly error.
        app.state.store = None
        app.state.llm = None
        logger.error("Failed to initialize RAG backend: %s", e)
    yield


app = FastAPI(title="ABC123 Restaurant — RAG Web UI", lifespan=lifespan)

# Register the page routes (HTML) and the API routes (JSON) from their own files.
app.include_router(page_router)
app.include_router(api_router)

# --- Static assets ---------------------------------------------------------------
# Serves anything inside the static/ folder at the /static/ URL path.
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

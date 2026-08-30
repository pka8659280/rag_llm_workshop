# -*- coding: utf-8 -*-
"""Page routes (HTML) for the ABC123 Restaurant RAG pipeline.

Sends the browser the two static HTML pages:
  GET /         -> static/chat.html     (chat with the RAG chatbot)
  GET /reviews  -> static/reviews.html  (browse / filter / search reviews in Qdrant)

Imported by web_app.py (which owns the FastAPI app + startup logic).
"""
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

# Folder that contains this file — the static/ subfolder lives next to it.
BASE_DIR = Path(__file__).resolve().parent

router = APIRouter()


@router.get("/")
def chat_page():
    """Send the chat HTML page to the browser."""
    return FileResponse(BASE_DIR / "static" / "chat.html")


@router.get("/reviews")
def reviews_page():
    """Send the review-browser HTML page to the browser."""
    return FileResponse(BASE_DIR / "static" / "reviews.html")

# -*- coding: utf-8 -*-
"""
Web UI for the ABC123 Restaurant RAG pipeline — FastAPI.

Serves two pages:
  GET /         -> static/chat.html     (chat with the RAG chatbot)
  GET /reviews  -> static/reviews.html  (browse / filter / search reviews in Qdrant)

APIs:
  POST /api/chat    {"question": str}                        -> {"answer": str}
  GET  /api/reviews ?limit&offset&star_rating&dish_mentioned
                    &order_type&q                            -> {"total", "points"}
  POST /api/search  {"query": str, "k": int}                 -> {"query", "results": [...]}

Reuses the LangChain vector store + LLM from chat.py (single source of truth).
Run with:  uvicorn web_app:app --port 8000
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from chat import COLLECTION_NAME, TOP_K, answer, build

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("web_app")

BASE_DIR = Path(__file__).resolve().parent

# --- Request models -----------------------------------------------------------


class ChatRequest(BaseModel):
    """Body for POST /api/chat: the user's question."""

    question: str = Field(..., min_length=1)


class SearchRequest(BaseModel):
    """Body for POST /api/search: a free-text query plus how many hits to return."""

    query: str = Field(..., min_length=1)
    k: int = Field(default=TOP_K, ge=1, le=10)


# --- App + startup -------------------------------------------------------------
# build() comes from chat.py; on failure it calls sys.exit(1) (raises SystemExit),
# so we catch it here and keep serving — the /api endpoints then return a 500 JSON
# error with a clear message instead of crashing the server.


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.store, app.state.llm = build()
        logger.info("RAG backend initialized (collection=%s).", COLLECTION_NAME)
    except (Exception, SystemExit) as e:
        app.state.store = None
        app.state.llm = None
        logger.error("Failed to initialize RAG backend: %s", e)
    yield


app = FastAPI(title="ABC123 Restaurant — RAG Web UI", lifespan=lifespan)


# --- Pages ----------------------------------------------------------------------


@app.get("/")
def chat_page():
    return FileResponse(BASE_DIR / "static" / "chat.html")


@app.get("/reviews")
def reviews_page():
    return FileResponse(BASE_DIR / "static" / "reviews.html")


# --- APIs -----------------------------------------------------------------------


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    """Answer a restaurant question using the same RAG chain as chat.py."""
    if app.state.store is None:
        raise HTTPException(
            500,
            "RAG backend not initialized. Check that Qdrant (port 6333) and Ollama are running.",
        )
    try:
        return {"answer": answer(app.state.store, app.state.llm, req.question)}
    except Exception as e:
        logger.error("Chat error: %s", e)
        raise HTTPException(500, f"Chat failed: {e}") from e


def _all_points():
    """Return every point in the collection (only ~100 rows, so one scroll is fine)."""
    points, _ = app.state.store.client.scroll(
        collection_name=COLLECTION_NAME,
        limit=10000,
        with_payload=True,
        with_vectors=False,
    )
    return points


@app.get("/api/reviews")
def api_reviews(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    star_rating: int | None = Query(default=None, ge=1, le=5),
    dish_mentioned: str | None = None,
    order_type: str | None = None,
    q: str | None = None,
):
    """List reviews from Qdrant with optional filters and pagination."""
    if app.state.store is None:
        raise HTTPException(500, "Qdrant is not reachable. Check that the Qdrant container is running.")
    try:
        rows = []
        for p in _all_points():
            payload = p.payload or {}
            # langchain-qdrant stores the document metadata under a nested "metadata" key.
            meta = payload.get("metadata") or {}
            if star_rating is not None and meta.get("star_rating") != star_rating:
                continue
            if dish_mentioned and dish_mentioned.lower() not in str(meta.get("dish_mentioned", "")).lower():
                continue
            if order_type and str(meta.get("order_type", "")).lower() != order_type.lower():
                continue
            if q:
                haystack = f"{payload.get('page_content', '')} {meta.get('reviewer_name', '')}".lower()
                if q.lower() not in haystack:
                    continue
            rows.append(
                {
                    "review_id": meta.get("review_id"),
                    "review_date": meta.get("review_date"),
                    "reviewer_name": meta.get("reviewer_name"),
                    "star_rating": meta.get("star_rating"),
                    "visit_date": meta.get("visit_date"),
                    "reviewer_location": meta.get("reviewer_location"),
                    "order_type": meta.get("order_type"),
                    "dish_mentioned": meta.get("dish_mentioned"),
                    "text": payload.get("page_content", ""),
                }
            )
        return {"total": len(rows), "points": rows[offset : offset + limit]}
    except Exception as e:
        logger.error("Reviews error: %s", e)
        raise HTTPException(500, f"Failed to read reviews from Qdrant: {e}") from e


@app.post("/api/search")
def api_search(req: SearchRequest):
    """Semantic (vector) search over the reviews, returning top-k matches + scores."""
    if app.state.store is None:
        raise HTTPException(
            500,
            "RAG backend not initialized. Check that Qdrant (port 6333) and Ollama are running.",
        )
    try:
        hits = app.state.store.similarity_search_with_score(req.query, k=req.k)
        results = [
            {"metadata": doc.metadata, "text": doc.page_content, "score": round(float(score), 4)}
            for doc, score in hits
        ]
        return {"query": req.query, "results": results}
    except Exception as e:
        logger.error("Search error: %s", e)
        raise HTTPException(500, f"Similarity search failed: {e}") from e


# --- Static assets ---------------------------------------------------------------
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

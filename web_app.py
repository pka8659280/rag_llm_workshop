# -*- coding: utf-8 -*-
"""
Web UI for the ABC123 Restaurant RAG pipeline — FastAPI.

Serves two pages:
  GET /         -> static/chat.html     (chat with the RAG chatbot)
  GET /reviews  -> static/reviews.html  (browse / filter / search reviews in Qdrant)

APIs (what the JavaScript on those pages calls):
  POST /api/chat    {"question": str}                        -> {"answer": str}
  GET  /api/reviews ?limit&offset&star_rating&dish_mentioned
                    &order_type&q                            -> {"total", "points"}
  POST /api/search  {"query": str, "k": int}                 -> {"query", "results": [...]}

It reuses the LangChain vector store + LLM from chat.py (single source of truth),
so the chatbot logic is not duplicated here.

Run with:  uvicorn web_app:app --port 8000
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

# --- FastAPI ------------------------------------------------------------------
from fastapi import FastAPI, HTTPException, Query  # HTTPException = return an error response with a status code
from fastapi.responses import FileResponse  # sends an HTML file to the browser
from fastapi.staticfiles import StaticFiles  # serves the /static folder (images, css, ...)
# --- Pydantic (request validation) ----------------------------------------------
from pydantic import BaseModel, Field

# --- Our own RAG code -----------------------------------------------------------
from chat import COLLECTION_NAME, TOP_K, answer, build

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("web_app")

BASE_DIR = Path(__file__).resolve().parent  # folder that contains web_app.py

# --- Request models -------------------------------------------------------------
# These classes define the JSON body the browser must send. FastAPI validates
# the incoming JSON against them and turns it into a Python object.
class ChatRequest(BaseModel):
    """Body for POST /api/chat: the user's question."""

    question: str = Field(..., min_length=1)  # required, must not be empty


class SearchRequest(BaseModel):
    """Body for POST /api/search: a free-text query plus how many hits to return."""

    query: str = Field(..., min_length=1)  # required, must not be empty
    k: int = Field(default=TOP_K, ge=1, le=10)  # 1..10 hits, defaults to TOP_K


# --- App + startup ---------------------------------------------------------------
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


# --- Pages (HTML) ------------------------------------------------------------------
@app.get("/")
def chat_page():
    """Send the chat HTML page to the browser."""
    return FileResponse(BASE_DIR / "static" / "chat.html")


@app.get("/reviews")
def reviews_page():
    """Send the review-browser HTML page to the browser."""
    return FileResponse(BASE_DIR / "static" / "reviews.html")


# --- APIs (JSON) -------------------------------------------------------------------
@app.post("/api/chat")
def api_chat(req: ChatRequest):
    """Answer a restaurant question using the same RAG chain as chat.py."""
    if app.state.store is None:
        raise HTTPException(
            500,
            "RAG backend not initialized. Check that Qdrant (port 6333) and Ollama are running.",
        )
    try:
        # answer() = retrieve similar reviews from Qdrant, then ask the LLM.
        return {"answer": answer(app.state.store, app.state.llm, req.question)}
    except Exception as e:
        # 500 = "server error". The frontend shows this message to the user.
        logger.error("Chat error: %s", e)
        raise HTTPException(500, f"Chat failed: {e}") from e


def _all_points():
    """Return every point in the collection (only ~100 rows, so one scroll is fine).

    scroll() is Qdrant's way of listing all stored points.
    with_payload=True -> include the stored review data.
    with_vectors=False -> skip the heavy embedding vectors (we don't need them here).
    """
    points, _ = app.state.store.client.scroll(
        collection_name=COLLECTION_NAME,
        limit=10000,
        with_payload=True,
        with_vectors=False,
    )
    return points


@app.get("/api/reviews")
def api_reviews(
    limit: int = Query(default=20, ge=1, le=100),       # rows per page (1..100)
    offset: int = Query(default=0, ge=0),               # skip this many rows (pagination)
    star_rating: int | None = Query(default=None, ge=1, le=5),  # optional filter
    dish_mentioned: str | None = None,                  # optional filter (substring)
    order_type: str | None = None,                      # optional filter (exact)
    q: str | None = None,                               # optional free-text filter
):
    """List reviews from Qdrant with optional filters and pagination."""
    if app.state.store is None:
        raise HTTPException(500, "Qdrant is not reachable. Check that the Qdrant container is running.")
    try:
        rows = []
        for p in _all_points():
            payload = p.payload or {}
            # langchain-qdrant stores the document metadata under a nested
            # "metadata" key inside the payload, so we read it from there.
            meta = payload.get("metadata") or {}
            # --- apply filters (skip this row if it does not match) ---
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
            # --- keep the fields the frontend displays ---
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
        # total = all matching rows; points = only the slice for the current page.
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
        # Embed the query and ask Qdrant for the k closest reviews.
        # Returns (Document, score) pairs; score = cosine similarity (0..1).
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
# Serves anything inside the static/ folder at the /static/ URL path.
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# -*- coding: utf-8 -*-
"""API endpoints (JSON) for the ABC123 Restaurant RAG pipeline.

The JavaScript on the HTML pages calls these:
  POST /api/chat    {"question": str}                        -> {"answer": str}
  GET  /api/reviews ?limit&offset&star_rating&dish_mentioned
                    &order_type&q                            -> {"total", "points"}
  POST /api/search  {"query": str, "k": int}                 -> {"query", "results": [...]}
  GET  /api/spreadsheets                                     -> {"files": [filename, ...]}
  POST /api/convert  {"file": str | omitted}                 -> {"file", "converted", "points"}
  POST /api/data/clear (no body)                             -> {"removed", "points"}

The RAG objects (Qdrant store + LLM) live on app.state, created once in web_app.py's
startup; the endpoints read them via `request.app.state` so the routers stay stateless.

Imported by web_app.py (which owns the FastAPI app + startup logic).
"""
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

# Reuses the LangChain vector store + LLM from chat.py (single source of truth),
# so the chatbot logic is not duplicated here.
from chat import COLLECTION_NAME, TOP_K, answer
# Reuses the Excel -> Qdrant ingestion function (single source of truth), so the
# web page can trigger the same conversion as python embedding.py.
from converter import convert_excel_to_qdrant

logger = logging.getLogger("api_routes")
router = APIRouter()

# Absolute path to the folder that holds the spreadsheets (project root / spreadsheet_data),
# so it works no matter which directory uvicorn was started from.
SPREADSHEET_DIR = Path(__file__).resolve().parent.parent / "spreadsheet_data"


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


class ConvertRequest(BaseModel):
    """Body for POST /api/convert: which spreadsheet file to ingest (optional).

    If `file` is omitted, the first spreadsheet found in spreadsheet_data/ is used,
    which keeps the old "empty body" behaviour working.
    """

    file: str | None = None  # filename, e.g. "ABC123_..._100_Rows.xlsx"


# --- Chat -----------------------------------------------------------------------
@router.post("/api/chat")
def api_chat(req: ChatRequest, request: Request):
    """Answer a restaurant question using the same RAG chain as chat.py."""
    if request.app.state.store is None:
        raise HTTPException(
            500,
            "RAG backend not initialized. Check that Qdrant (port 6333) and Ollama are running.",
        )
    try:
        # answer() = retrieve similar reviews from Qdrant, then ask the LLM.
        return {"answer": answer(request.app.state.store, request.app.state.llm, req.question)}
    except Exception as e:
        # 500 = "server error". The frontend shows this message to the user.
        logger.error("Chat error: %s", e)
        raise HTTPException(500, f"Chat failed: {e}") from e


# --- Reviews (browse / filter) ----------------------------------------------------
def _all_points(request: Request):
    """Return every point in the collection (only ~100 rows, so one scroll is fine).

    scroll() is Qdrant's way of listing all stored points.
    with_payload=True -> include the stored review data.
    with_vectors=False -> skip the heavy embedding vectors (we don't need them here).
    """
    points, _ = request.app.state.store.client.scroll(
        collection_name=COLLECTION_NAME,
        limit=10000,
        with_payload=True,
        with_vectors=False,
    )
    return points


@router.get("/api/reviews")
def api_reviews(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),       # rows per page (1..100)
    offset: int = Query(default=0, ge=0),               # skip this many rows (pagination)
    star_rating: int | None = Query(default=None, ge=1, le=5),  # optional filter
    dish_mentioned: str | None = None,                  # optional filter (substring)
    order_type: str | None = None,                      # optional filter (exact)
    q: str | None = None,                               # optional free-text filter
):
    """List reviews from Qdrant with optional filters and pagination."""
    if request.app.state.store is None:
        raise HTTPException(500, "Qdrant is not reachable. Check that the Qdrant container is running.")
    try:
        rows = []
        for p in _all_points(request):
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


# --- Semantic (vector) search -------------------------------------------------------
@router.post("/api/search")
def api_search(req: SearchRequest, request: Request):
    """Semantic (vector) search over the reviews, returning top-k matches + scores."""
    if request.app.state.store is None:
        raise HTTPException(
            500,
            "RAG backend not initialized. Check that Qdrant (port 6333) and Ollama are running.",
        )
    try:
        # Embed the query and ask Qdrant for the k closest reviews.
        # Returns (Document, score) pairs; score = cosine similarity (0..1).
        hits = request.app.state.store.similarity_search_with_score(req.query, k=req.k)
        results = [
            {"metadata": doc.metadata, "text": doc.page_content, "score": round(float(score), 4)}
            for doc, score in hits
        ]
        return {"query": req.query, "results": results}
    except Exception as e:
        logger.error("Search error: %s", e)
        raise HTTPException(500, f"Similarity search failed: {e}") from e


# --- Convert (ingest a spreadsheet into the vector DB) ----------------------------
# The browser dropdown lists the files via /api/spreadsheets and sends the selected
# filename to /api/convert. No dependency on app.state either — convert_excel_to_qdrant()
# builds its own vector store, and because it upserts the same deterministic UUID5 ids,
# the existing store on app.state keeps pointing at valid (updated) data.
@router.get("/api/spreadsheets")
def api_spreadsheets():
    """List the spreadsheet files (.xlsx/.xls/.xlsm) in the spreadsheet_data/ folder."""
    if not SPREADSHEET_DIR.is_dir():
        return {"files": []}
    files = sorted(
        p.name for p in SPREADSHEET_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in (".xlsx", ".xls", ".xlsm")
    )
    return {"files": files}


@router.post("/api/convert")
def api_convert(req: ConvertRequest):
    """Re-ingest a spreadsheet from spreadsheet_data/ into 'restaurant_reviews' (idempotent)."""
    # Path(file).name strips any directory part, so a value like "..\\..\\evil.xlsx"
    # can never escape the spreadsheet_data/ folder (path-traversal guard).
    if req.file:
        name = Path(req.file).name
        path = SPREADSHEET_DIR / name
        if not path.is_file():
            raise HTTPException(400, f"File '{name}' not found in spreadsheet_data/.")
    else:
        files = api_spreadsheets()["files"]
        if not files:
            raise HTTPException(400, "No spreadsheet found in spreadsheet_data/.")
        name = files[0]  # no file chosen -> convert the first spreadsheet (alphabetical)
        path = SPREADSHEET_DIR / name
    try:
        summary = convert_excel_to_qdrant(excel_file=str(path))
        return {"file": name, **summary}
    except Exception as e:
        logger.error("Convert error: %s", e)
        raise HTTPException(500, f"Conversion failed: {e}") from e


# --- Data removal (delete points from the vector DB) -------------------------------
# Points are keyed by deterministic UUID5 ids, so removing them and re-ingesting the
# same spreadsheet re-creates them at the same ids (idempotent, no duplicates).
@router.post("/api/data/clear")
def api_clear_data(request: Request):
    """Delete ALL points from 'restaurant_reviews' (full reset of the vector data)."""
    if request.app.state.store is None:
        raise HTTPException(
            500,
            "RAG backend not initialized. Check that Qdrant (port 6333) and Ollama are running.",
        )
    try:
        ids = [p.id for p in _all_points(request)]
        if ids:
            request.app.state.store.client.delete(
                collection_name=COLLECTION_NAME, points_selector=ids
            )
        return {"removed": len(ids), "points": 0}
    except Exception as e:
        logger.error("Clear error: %s", e)
        raise HTTPException(500, f"Failed to clear data: {e}") from e

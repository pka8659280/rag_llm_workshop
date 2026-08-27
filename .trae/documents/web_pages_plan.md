# Plan: Two Web Pages — Chat UI + Vector DB Data Review

## Summary

Build a small FastAPI web application with **two pages**:

1. **Chat page** (`/`) — a chat interface that talks to the real RAG pipeline (`chat.py` logic) and answers restaurant questions.
2. **Vector DB review page** (`/reviews`) — a browsable table of all 100 reviews stored in Qdrant (collection `restaurant_reviews`), with filters (star rating, dish, order type), text search, pagination, and a similarity-search box showing top-k matches with relevance scores.

Both pages are plain HTML + vanilla JavaScript (no build tools). A single FastAPI backend (`web_app.py`) serves the pages and exposes the JSON APIs, reusing the existing LangChain code from `chat.py` so there is no duplication.

## Current State Analysis

- **Data in Qdrant**: collection `restaurant_reviews` (1024-dim, Cosine), 100 points. Each point's payload: `review_id`, `review_date`, `reviewer_name`, `star_rating`, `visit_date`, `reviewer_location`, `order_type`, `dish_mentioned`, and `page_content` = the review text. See [embedding.py](file:///c:/Users/User/VisualStudioCodeWorkspace/rag_llm_workshop/embedding.py).
- **Chat logic**: [chat.py](file:///c:/Users/User/VisualStudioCodeWorkspace/rag_llm_workshop/chat.py) exposes `build()` → `(store, llm)` and `answer(store, llm, question)` → answer string. Constants: `QDRANT_URL=http://localhost:6333`, `COLLECTION_NAME=restaurant_reviews`, `EMBED_MODEL=qwen3-embedding:0.6b`, `CHAT_MODEL=qwen3.5:9b`, `TOP_K=4`. Safe to import (guard `if __name__ == "__main__"`).
- **Environment**: `fastapi` 0.115.8 and `uvicorn` 0.34.0 already installed; `langchain-qdrant`, `langchain-ollama`, `qdrant-client` 1.19.0 present.
- **Existing web asset**: none. `index.html` from a previous chat suggestion was never created.

## Proposed Changes

### 1. New file: `web_app.py` — FastAPI backend

Reuses `chat.py` functions via import (`from chat import build, answer`).

- **Startup (lifespan)**: call `build()` once, store `(store, llm)` in `app.state`. On failure, log error and keep serving with `/api/*` endpoints returning a 500 JSON error (do NOT `sys.exit`).
- **Routes**:
  - `GET /` → returns `static/chat.html`
  - `GET /reviews` → returns `static/reviews.html`
  - `POST /api/chat` — body `{"question": str}` → `{"answer": str}` (calls `answer()`; returns 500 JSON on exception)
  - `GET /api/reviews` — query params `limit` (default 20, max 100), `offset` (default 0), `star_rating` (int, optional), `dish_mentioned` (str, optional, substring), `order_type` (str, optional, exact), `q` (str, optional, substring search over review text + reviewer name). Implementation: `store.client.scroll(collection_name, limit=10000, with_payload=True, with_vectors=False)` once per request, filter in Python (only 100 points — simple and fast), then paginate. Returns `{"total": int, "points": [{review_id, review_date, reviewer_name, star_rating, visit_date, reviewer_location, order_type, dish_mentioned, text}]}`.
  - `POST /api/search` — body `{"query": str, "k": int (default 5, max 10)}` → `{"query": str, "results": [{metadata: {...}, text: str, score: float}]}` using `store.similarity_search_with_score(query, k=k)`.
- **Serving static files**: mount `StaticFiles(directory="static")` at `/static`, plus explicit routes for the two HTML pages.

### 2. New file: `static/chat.html` — Chat page

- Same gradient purple/blue visual theme as the earlier prototype, with a header ("ABC123 Restaurant — AI Review Assistant") and an "About this project" card.
- Chat area: message bubbles (bot left / user right), Enter-to-send, disabled send button while waiting, auto-scroll.
- JavaScript: `fetch("/api/chat", {method:"POST", body: JSON.stringify({question})})`, renders `answer`. Shows inline error banner if the backend is down or returns 500.

### 3. New file: `static/reviews.html` — Vector DB data review page

Sections (one page, top to bottom):

- **Header + stats bar**: total point count fetched from `/api/reviews` `total` (e.g., "100 reviews in Qdrant").
- **Filters bar**: star-rating dropdown (All/1–5), dish text input, order-type dropdown (All/dine-in/takeout/delivery — values read from actual data), free-text search input, plus "Reset" button.
- **Reviews table**: columns Reviewer, Rating (★ rendering), Review Date, Dish, Order Type, Location, Review Text. Rows paginated client-side-free: pagination controls (Prev/Next + page indicator) that re-request `/api/reviews` with `offset/limit`.
- **Similarity search box**: input + k selector + Search button; results rendered as cards below the table showing matched text, metadata summary, and relevance score (0–1), highlighting that these are vector-space matches.
- All data loaded via `fetch("/api/reviews")` / `fetch("/api/search")`. No framework.

### 4. New file: `Step_5_web_ui_run_guideline.md` — run guide (project convention)

Follows the existing `Step_N_[task]_run_guideline.md` convention (see `Step_3`/`Step_4`). Contents: prerequisites (Qdrant + Ollama running, models pulled, Step 3 done), how to start the server (`uvicorn web_app:app --port 8000`), how to open both pages, sample curl/Invoke-RestMethod commands for the 3 API endpoints, and troubleshooting table.

## Assumptions & Decisions

- **Backend = FastAPI + uvicorn** because both are already installed; no new dependencies needed (no Flask install).
- **Reuse `chat.py` via import** rather than copying its code, keeping one source of truth. Importing is safe because `chat.py`'s logic is under `if __name__ == "__main__"`.
- **Reviews page reads directly from Qdrant via `store.client.scroll`** (raw qdrant-client through the LangChain store), consistent with how `embedding.py` already uses `store.client.count(...)`.
- **Filtering done in Python** after a single full scroll (only 100 points), keeping the code simple instead of building Qdrant filter queries.
- **No authentication, no CORS needed** (same origin). Port **8000** default; port documented in the run guideline.
- **Documentation file is included** because the project convention is a `Step_N_..._run_guideline.md` per step; remove it from the plan if you do not want it.

## Verification

1. Preconditions: Qdrant running (`docker start qdrant`), Ollama running, collection populated (`python embedding.py`).
2. Start server: `uvicorn web_app:app --port 8000` — expect "Application startup complete".
3. Open `http://localhost:8000/` → chat page loads; send a restaurant question (e.g., "What do customers say about the laksa?") → real RAG answer; send an off-topic question → refusal message.
4. Open `http://localhost:8000/reviews` → table shows 100 reviews; test star-rating filter, dish search, order-type filter, free-text search, and pagination (verify `total` matches).
5. Run a similarity search (e.g., "best kolo mee", k=5) → results shown with scores.
6. API spot-checks with PowerShell:
   - `Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/chat -ContentType "application/json" -Body '{"question":"How is the service?"}'`
   - `Invoke-RestMethod -Uri "http://localhost:8000/api/reviews?star_rating=5&limit=5"`
   - `Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/search -ContentType "application/json" -Body '{"query":"kolo mee","k":3}'`
7. Negative check: stop Qdrant → `/api/reviews` returns a JSON 500 error with a clear message instead of crashing the server.

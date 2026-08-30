# Web UI Run Guideline (FastAPI — Chat Page + Vector DB Review Page)

## What It Does

- `WebApps/web_app.py` is a FastAPI server that exposes the RAG pipeline over HTTP and serves two pages:
  - **Chat page** (`http://localhost:8000/`) — talk to the ABC123 Restaurant chatbot (same logic as `chat.py`).
  - **Vector DB review page** (`http://localhost:8000/reviews`) — browse, filter, and semantically search the reviews stored in Qdrant.
- It reuses `chat.py` (`build()` / `answer()`) directly, so there is no duplicated logic.

## Prerequisite

- Step 2 done: Qdrant is running (see `Step_2_qdrant_installation_run_guideline.md`).
- Step 3 done: the reviews are embedded (see `Step_3_embedding_run_guideline.md`) → collection `restaurant_reviews` has 100 points.
- Ollama running with both models pulled:

```powershell
ollama pull qwen3-embedding:0.6b
ollama pull qwen3.5:9b
```

- Python packages installed (FastAPI and uvicorn are already in the environment; install once if missing):

```powershell
pip install fastapi uvicorn openpyxl langchain-ollama langchain-qdrant
```

## 1. Start the Web Server

- Open PowerShell, go to the project folder, and run:

```powershell
cd C:\Users\User\VisualStudioCodeWorkspace\rag_llm_workshop
uvicorn WebApps.web_app:app --port 8000
```

- Expected output (last lines):

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

- The first chat answer is slow (the 9B model loads into memory); subsequent answers are fast.

## 2. Use the Chat Page

- Open <http://localhost:8000/> in a browser.
- Type a restaurant question (e.g., "What do customers say about the laksa?") and press Enter.
- Off-topic questions are declined with the same refusal message as `chat.py`.

## 3. Use the Vector DB Review Page

- Open <http://localhost:8000/reviews> in a browser.
- Features:
  - **Stats bar** — total review count in Qdrant.
  - **Filters** — star rating, dish name (substring), order type, and free-text search over reviewer/review text.
  - **Table + pagination** — 20 rows per page with Prev/Next.
  - **Semantic search** — type a query, pick Top 3/5/10, and view the most similar reviews with relevance scores.

## 4. API Reference

| Endpoint | Method | Body / Params | Returns |
|---|---|---|---|
| `/api/chat` | POST | `{"question": "..."}` | `{"answer": "..."}` |
| `/api/reviews` | GET | `limit` (≤100), `offset`, `star_rating`, `dish_mentioned`, `order_type`, `q` | `{"total": n, "points": [...]}` |
| `/api/search` | POST | `{"query": "...", "k": 5}` | `{"query": "...", "results": [...]}` |

PowerShell examples:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/chat -ContentType "application/json" -Body '{"question":"How is the service?"}'

Invoke-RestMethod -Uri "http://localhost:8000/api/reviews?star_rating=5&limit=5"

Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/search -ContentType "application/json" -Body '{"query":"kolo mee","k":3}'
```

## Notes

- The server only reads from Qdrant; it never modifies the collection.
- If Qdrant/Ollama is down when the server starts, the server still starts — the `/api/*` endpoints return a JSON 500 error with a clear message instead of crashing.
- The two pages load Bootstrap 5 from the jsdelivr CDN, so the browser needs internet access to display the styled layout.
- Stop the server with `Ctrl+C` in the PowerShell window.

## Troubleshooting

| Error | Fix |
|---|---|
| `uvicorn: command not found` | Run `python -m uvicorn WebApps.web_app:app --port 8000` instead |
| Port 8000 already in use | Use another port, e.g. `uvicorn WebApps.web_app:app --port 8001` |
| `/api/chat` returns "RAG backend not initialized" | Qdrant is not running: `docker start qdrant` |
| Reviews page shows "Qdrant is not reachable" | Start Qdrant: `docker start qdrant` |
| Search/chat says model not found | Pull the models: `ollama pull qwen3.5:9b` and `ollama pull qwen3-embedding:0.6b` |
| Table is empty | The collection is empty; run `python embedding.py` (Step 3) first |

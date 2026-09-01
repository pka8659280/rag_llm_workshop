# ABC123 Restaurant — Google Reviews RAG Chatbot

A local RAG (Retrieval-Augmented Generation) pipeline that embeds 100 Google reviews
of ABC123 Restaurant (Kuching) into a Qdrant vector database, then lets you chat with
the data using LangChain + Ollama.

## Project Structure

| File | Purpose |
|---|---|
| `embedding.py` | Reads the review Excel, embeds each review with Ollama, and upserts vectors + metadata into Qdrant |
| `converter.py` | Reusable Excel → Qdrant ingestion function (used by `embedding.py` and the web `/api/convert` button) |
| `chat.py` | Restaurant-only Q&A chatbot that retrieves relevant reviews from Qdrant and answers with a LangChain LLM chain |
| `WebApps/web_app.py` | FastAPI entry point — starts the server, initializes the RAG backend, mounts routes |
| `WebApps/page_routes.py` | HTML pages: `/` (chat), `/reviews`, `/convert` |
| `WebApps/api_routes.py` | JSON endpoints: `/api/chat`, `/api/reviews`, `/api/search`, `/api/spreadsheets`, `/api/convert`, `/api/data/clear` |
| `WebApps/static/*.html` | Browser pages + shared FAB navigation menu |
| `spreadsheet_data/ABC123_Restaurant_Kuching_Google_Reviews_100_Rows.xlsx` | Source data (100 review rows, 9 columns); all spreadsheets live in `spreadsheet_data/` |
| `Guideline/Step_1_docker_installation_run_guideline.md` | Docker installation guide |
| `Guideline/Step_2_qdrant_installation_run_guideline.md` | Qdrant installation & run guide |
| `Guideline/Step_3_embedding_run_guideline.md` | Embedding run guide |
| `Guideline/Step_4_chat_run_guideline.md` | Chat run guide |
| `Guideline/Step_5_web_ui_run_guideline.md` | Web UI run guide |

## Tech Stack

- **Qdrant** — vector database (http://localhost:6333)
- **Ollama** — local models: `qwen3-embedding:0.6b` (embeddings, 1024-dim) and `qwen3.5:9b` (chat)
- **LangChain** — `langchain-ollama`, `langchain-qdrant`, `langchain-core`

## Quick Start

Prerequisites: Docker installed and running, Ollama installed.

1. **Docker** — follow `Guideline/Step_1_docker_installation_run_guideline.md`.
2. **Qdrant** — follow `Guideline/Step_2_qdrant_installation_run_guideline.md` to start Qdrant on port 6333.
3. **Pull the Ollama models:**
   ```powershell
   ollama pull qwen3-embedding:0.6b
   ollama pull qwen3.5:9b
   ```
4. **Install Python packages:**
   ```powershell
   pip install openpyxl langchain-ollama langchain-qdrant fastapi uvicorn
   ```
5. **Embed the reviews** (creates the `restaurant_reviews` collection; reads the
   spreadsheet from the `spreadsheet_data/` folder):
   ```powershell
   python embedding.py
   ```
   Expected output: `Embedded 100 reviews into 'restaurant_reviews' (100 points in Qdrant).`
6. **Chat with the data (CLI):**
   ```powershell
   python chat.py                        # interactive REPL
   python chat.py "What do customers say about the kolo mee?"   # one question
   ```
7. **Start the web app** (chat UI + reviews browser + Convert page):
   ```powershell
   uvicorn WebApps.web_app:app --port 8000
   ```
8. **Open the pages in a browser:**
   - **Chat** — http://localhost:8000/
   - **Reviews** — http://localhost:8000/reviews
   - **Convert** — http://localhost:8000/convert (pick a spreadsheet from the dropdown, then the button re-ingests it into Qdrant, no need to run `embedding.py`)

   The three pages share a floating action button (⚙️) to navigate between them.

## Usage Notes

- `embedding.py` is idempotent: re-running updates existing points (deterministic
  UUID5 IDs), so it never creates duplicates.
- `chat.py` only reads from Qdrant and only answers restaurant-related questions;
  unrelated questions are politely declined.
- The chatbot is not limited to the review content — it may also use general
  knowledge about the restaurant.
- The web **Convert** page (`/convert`) does the same idempotent ingestion as
  `embedding.py`, so re-running it never creates duplicate points.
- The **Remove Data** section on `/convert` has a **Remove All** button that deletes every
  point from the vector DB. Re-converting a spreadsheet re-adds the same points (deterministic
  IDs), so removal is reversible.

## Troubleshooting

- **Qdrant not reachable** (`connection refused`) — start it: `docker start qdrant`
- **Model not found** — pull it with `ollama pull <model>`
- **Collection missing** — run `python embedding.py` first
- **Slow first chat answer** — the 9B chat model needs to load into memory; subsequent answers are faster
- **Web app won't start with an `on_startup` error** — upgrade fastapi/starlette to their latest versions (`pip install --upgrade fastapi`); check for dependency conflicts with `pip check`
- **Port 8000 already in use** — pick another port: `uvicorn WebApps.web_app:app --port 8001`

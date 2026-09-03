# ABC123 Restaurant — Google Reviews RAG Chatbot

A local RAG (Retrieval-Augmented Generation) pipeline that embeds 100 Google reviews
of ABC123 Restaurant (Kuching) into a Qdrant vector database, then lets you chat with
the data using LangChain + Ollama.

> **Education Purpose** — This project was built as a hands-on learning example of a
> local RAG pipeline. The review data in `spreadsheet_data/` is **synthetic/AI-generated
> demo data**, not real Google reviews; any resemblance to real people or businesses is
> coincidental.

## Run with Docker

Docker is the only way you need to run the app — Qdrant and Ollama are started
automatically, so nothing else needs to be installed on the target device.

Copy this whole project folder to the device that has Docker, then run:

1. **Build the Docker image** (first run only — or whenever you change the code):
   ```powershell
   docker compose build
   ```

2. **Run everything** — starts Qdrant + Ollama + the web app, downloads the qwen
   models on the very first run (~5.5 GB), and auto-embeds the 100 reviews:
   ```powershell
   docker compose up -d
   ```

   **Watching the first-run model download (~5.5 GB):** the download runs in a dedicated
   one-shot `models` service (container `rag-models`), so its progress is easy to see:
   - **Recommended on the very first run:** use `docker compose up` (no `-d`) so the
     download progress prints live in the terminal. After it finishes, press `Ctrl+C` and
     use `docker compose up -d` on later runs.
   - Or keep `docker compose up -d` and open a second terminal with
     `docker compose logs -f models` to watch the download.
   - While the download runs, `docker compose up` shows `rag-seed Waiting` — that is
     normal: seeding (auto-embedding) only starts after the models finish.

Then open http://localhost:8000/ to chat.

If a step fails (build error, container won't start, etc.), don't retry on a
half-created stack — stop and remove everything first, then run the steps again:

```powershell
docker compose down -v
docker rmi -f abc123-rag-webapp qdrant/qdrant ollama/ollama
```

## Remove Everything (Full Cleanup)

To stop the app and delete everything Docker created — containers, the compose
network, the stored reviews, the downloaded qwen models (~5.5 GB), and the images:

```powershell
docker compose down -v
docker rmi abc123-rag-webapp qdrant/qdrant ollama/ollama
```

`down -v` stops and removes the containers, the compose network, and the named
volumes (`qdrant_data` = embedded reviews, `ollama_data` = the qwen models).
`rmi` then deletes the built `abc123-rag-webapp` image plus the Qdrant and Ollama
base images. The project folder on disk is untouched.

The next `docker compose up -d` is a full first run again: it rebuilds the image,
re-downloads the models (~5.5 GB), and auto-embeds the 100 reviews.

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
| `Dockerfile` | Builds the `abc123-rag-webapp` image (Python 3.11 + pinned requirements + the app) |
| `docker-compose.yml` | Orchestrates the full stack: qdrant + ollama + webapp + one-shot `models` (model downloader) + one-shot `seed` services |
| `deploy_seed.py` | Auto-seed runner used by the `seed` service: waits for the qwen models, then embeds the reviews |
| `Guideline/Step_1_docker_installation_run_guideline.md` | Docker installation guide |
| `Guideline/Step_2_qdrant_installation_run_guideline.md` | Qdrant installation & run guide |
| `Guideline/Step_3_embedding_run_guideline.md` | Embedding run guide |
| `Guideline/Step_4_chat_run_guideline.md` | Chat run guide |
| `Guideline/Step_5_web_ui_run_guideline.md` | Web UI run guide |

## Tech Stack

- **Qdrant** — vector database (http://localhost:6333)
- **Ollama** — local models: `qwen3-embedding:0.6b` (embeddings, 1024-dim) and `qwen3.5:9b` (chat)
- **LangChain** — `langchain-ollama`, `langchain-qdrant`, `langchain-core`

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
- **First run seems stuck (`rag-seed Waiting`)** — normal: the `models` service is downloading ~5.5 GB; watch it with `docker compose logs -f models`
- **Collection missing** — run `python embedding.py` first
- **Slow first chat answer** — the 9B chat model needs to load into memory; subsequent answers are faster
- **Web app won't start with an `on_startup` error** — upgrade fastapi/starlette to their latest versions (`pip install --upgrade fastapi`); check for dependency conflicts with `pip check`
- **Port 8000 already in use** — pick another port: `uvicorn WebApps.web_app:app --port 8001`

## License

MIT — see [LICENSE](LICENSE).

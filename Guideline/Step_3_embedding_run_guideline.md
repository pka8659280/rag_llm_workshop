# Embedding Run Guideline (Excel Data → Qdrant)

## What It Does

- Reads the 100 Google review rows from:
  - `spreadsheet_data/ABC123_Restaurant_Kuching_Google_Reviews_100_Rows.xlsx`
- Embeds each review's text using Ollama (`qwen3-embedding:0.6b`).
- Upserts vectors + metadata into the Qdrant collection `restaurant_reviews`.

## Prerequisite

- Qdrant must be running (see `Step_2_qdrant_installation_run_guideline.md`).
- Ollama must be installed and running, with the embedding model pulled:

```powershell
ollama pull qwen3-embedding:0.6b
```

- Python packages installed:

```powershell
pip install openpyxl langchain-ollama langchain-qdrant
```

## 1. Run the Embedding Script

- Open PowerShell, go to the project folder, and run:

```powershell
# Navigate to the folder where you cloned this repo first
cd <your-project-folder>
python embedding.py
```

- Expected output:

```
Embedded 100 reviews into 'restaurant_reviews' (100 points in Qdrant).
```

## 2. Verify the Data in Qdrant

### Option A — Dashboard

Open <http://localhost:6333/dashboard> → click `restaurant_reviews`.

### Option B — PowerShell (Point Count)

```powershell
(Invoke-RestMethod -Uri "http://localhost:6333/collections/restaurant_reviews").result.points_count
```

Expected: `100`

### Option C — Similarity Search (Optional, uses the same LangChain stack)

```python
from langchain_ollama import OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore
vs = QdrantVectorStore.from_existing_collection(
    collection_name='restaurant_reviews',
    embedding=OllamaEmbeddings(model='qwen3-embedding:0.6b'),
    url='http://localhost:6333')
for d in vs.similarity_search('best kolo mee', k=3):
    print(d.metadata['review_id'], '|', d.page_content)
```

## Notes

- Re-running is safe: point IDs are deterministic (UUID5 from `review_id`), so re-runs update existing points instead of creating duplicates.
- The collection is created automatically on the first run (1024-dim, Cosine).

## Troubleshooting

| Error                                            | Fix                                                              |
| ------------------------------------------------ | ---------------------------------------------------------------- |
| "Connection refused" to localhost:6333           | Qdrant is not running; start it with: `docker start qdrant`      |
| "model 'qwen3-embedding:0.6b' not found"         | Pull the model first: `ollama pull qwen3-embedding:0.6b`         |
| "No module named openpyxl"                       | `pip install openpyxl`                                           |
| "No module named langchain_qdrant"               | `pip install langchain-qdrant`                                   |

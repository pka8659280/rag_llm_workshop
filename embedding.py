# -*- coding: utf-8 -*-
"""
Embed the Excel Google review rows into Qdrant — vector store fully via LangChain.

1. Read the workbook with openpyxl.
2. Wrap each review as a LangChain Document.
3. QdrantVectorStore.from_documents auto-creates the collection (infers vector
   size), embeds with Ollama qwen3-embedding:0.6b, and upserts all documents.
"""
import datetime
import uuid

from openpyxl import load_workbook
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore

EXCEL_FILE = "ABC123_Restaurant_Kuching_Google_Reviews_100_Rows.xlsx"
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "restaurant_reviews"
EMBED_MODEL = "qwen3-embedding:0.6b"

# 1. Read the reviews and wrap each as a LangChain Document (text to embed + metadata).
wb = load_workbook(EXCEL_FILE)
rows = list(wb.active.iter_rows(values_only=True))
headers = rows[0]
documents = []
for values in rows[1:]:
    if not values or values[0] is None:
        continue
    row = dict(zip(headers, values))
    for key in ("Review Date", "Visit Date"):  # dates -> ISO strings for JSON payloads
        row[key] = row[key].strftime("%Y-%m-%d") if isinstance(row[key], datetime.datetime) else str(row[key])
    row["Star Rating"] = int(row["Star Rating"])
    documents.append(
        Document(
            page_content=row["Review Text"],
            metadata={
                "review_id": row["Review ID"],
                "review_date": row["Review Date"],
                "reviewer_name": row["Reviewer Name"],
                "star_rating": row["Star Rating"],
                "visit_date": row["Visit Date"],
                "reviewer_location": row["Reviewer Location"],
                "order_type": row["Order Type"],
                "dish_mentioned": row["Dish Mentioned"],
            },
        )
    )

# 2. Embed, auto-create the collection, and upsert — all through LangChain.
# Deterministic ids from review_id make re-runs idempotent (no duplicates).
ids = [str(uuid.uuid5(uuid.NAMESPACE_URL, d.metadata["review_id"])) for d in documents]
store = QdrantVectorStore.from_documents(
    documents,
    embedding=OllamaEmbeddings(model=EMBED_MODEL),
    url=QDRANT_URL,
    collection_name=COLLECTION_NAME,
    ids=ids,
)

count = store.client.count(COLLECTION_NAME).count
print(f"Embedded {len(documents)} reviews into '{COLLECTION_NAME}' ({count} points in Qdrant).")

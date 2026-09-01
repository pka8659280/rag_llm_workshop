# -*- coding: utf-8 -*-
"""
Embed the Excel Google review rows into Qdrant — the "ingest" step of the RAG pipeline.

This script is a thin CLI wrapper around the reusable function
convert_excel_to_qdrant() in converter.py (the single source of truth).

Key concepts (beginner note):
  - Embedding: turning a piece of TEXT into a list of numbers (a "vector") that
    captures its meaning. Similar texts get similar vectors.
  - Vector store: a database that stores those vectors and can later find the
    most similar ones to a new text (chat.py uses it for retrieval).
  - Idempotent: safe to run more than once — running it again with the same data
    updates the existing points instead of creating duplicates.

Run with:  python embedding.py
"""
from converter import COLLECTION_NAME, convert_excel_to_qdrant

if __name__ == "__main__":
    summary = convert_excel_to_qdrant()
    print(f"Embedded {summary['converted']} reviews into '{COLLECTION_NAME}' ({summary['points']} points in Qdrant).")

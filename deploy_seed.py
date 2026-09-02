# -*- coding: utf-8 -*-
"""
Auto-seed the ABC123 Restaurant review collection (runs as the one-shot "seed"
Docker Compose service).

What it does:
  1. Waits until Ollama has both qwen models pulled (first run downloads ~5.5 GB).
  2. Waits until Qdrant is reachable.
  3. If the 'restaurant_reviews' collection already has reviews -> skip. This
     keeps later starts fast, and the real conversion is idempotent anyway.
  4. Otherwise embeds the Excel reviews into Qdrant via converter.py — the exact
     same code path that embedding.py and the web /convert button use.

Run inside the container:  python deploy_seed.py
"""
import json
import os
import sys
import time
import urllib.request
from urllib.error import HTTPError

from converter import COLLECTION_NAME, convert_excel_to_qdrant

# Same environment plumbing as chat.py / converter.py (localhost = local dev).
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

# The two models the RAG pipeline needs (embeddings + chat).
REQUIRED_MODELS = {"qwen3-embedding:0.6b", "qwen3.5:9b"}

# The first run downloads ~5.5 GB of models, so allow a long window.
MODEL_TIMEOUT_SECONDS = 30 * 60
# How long to retry Qdrant before giving up.
QDRANT_TIMEOUT_SECONDS = 60


def _get_json(url: str) -> dict:
    """GET a URL and return the parsed JSON body (raises on HTTP/network errors)."""
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.load(response)


def wait_for_models() -> None:
    """Block until Ollama reports that both required models are available."""
    print(f"Waiting for Ollama models: {', '.join(sorted(REQUIRED_MODELS))} "
          "(first run downloads ~5.5 GB) ...", flush=True)
    deadline = time.time() + MODEL_TIMEOUT_SECONDS
    while time.time() < deadline:
        try:
            tags = _get_json(f"{OLLAMA_BASE_URL}/api/tags")
            available = {m["name"] for m in tags.get("models", [])}
            if REQUIRED_MODELS <= available:
                print("Ollama models are ready.", flush=True)
                return
        except Exception:
            pass  # Ollama not up yet - keep polling
        time.sleep(10)
    print("ERROR: Ollama models were not ready after 30 minutes.\n"
          "Check with: docker compose logs ollama", file=sys.stderr)
    sys.exit(1)


def qdrant_already_seeded() -> bool:
    """Return True when Qdrant is up AND the collection already has reviews."""
    url = f"{QDRANT_URL}/collections/{COLLECTION_NAME}"
    deadline = time.time() + QDRANT_TIMEOUT_SECONDS
    while time.time() < deadline:
        try:
            info = _get_json(url)
            result = info.get("result") or {}
            # points_count exists on current Qdrant; fall back to vectors_count
            # for older versions just in case.
            count = result.get("points_count")
            if count is None:
                vectors = result.get("vectors_count")
                count = sum(vectors.values()) if isinstance(vectors, dict) else (vectors or 0)
            return int(count or 0) > 0
        except HTTPError as error:
            if error.code == 404:
                # Collection does not exist yet -> convert_excel_to_qdrant()
                # creates it below, so "not seeded yet" is the correct answer.
                return False
            # Other HTTP errors (e.g. Qdrant still warming up): keep polling.
        except Exception:
            pass  # Qdrant not reachable yet - keep polling
        time.sleep(5)
    print("ERROR: Qdrant was not reachable within 60 seconds.\n"
          "Check with: docker compose logs qdrant", file=sys.stderr)
    sys.exit(1)


def main():
    wait_for_models()
    if qdrant_already_seeded():
        print("Reviews are already in Qdrant - skipping (idempotent).", flush=True)
        return
    print("Embedding the Excel reviews into Qdrant (first run only) ...", flush=True)
    summary = convert_excel_to_qdrant()
    print(f"Done: embedded {summary['converted']} reviews "
          f"-> {summary['points']} points in Qdrant.", flush=True)


if __name__ == "__main__":
    main()

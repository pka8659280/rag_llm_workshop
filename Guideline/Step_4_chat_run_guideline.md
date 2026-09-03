# Chat Run Guideline (RAG Chatbot — LangChain + Qdrant + Ollama)

## What It Does

- `chat.py` is a question-answering chatbot for **ABC123 Restaurant** in Kuching.
- It retrieves the most relevant Google reviews from Qdrant (collection `restaurant_reviews`) and answers using LangChain:
  - `QdrantVectorStore` (retrieval) + `OllamaEmbeddings` + `ChatOllama` + LCEL chain.
- It **only answers restaurant-related questions**; unrelated questions are declined.
- It is **NOT limited to the reviews**: the assistant may also use general knowledge about the restaurant when the reviews do not cover the question.

## Prerequisite

- Step 2 done: Qdrant is running (see `Step_2_qdrant_installation_run_guideline.md`).
- Step 3 done: the reviews are embedded (see `Step_3_embedding_run_guideline.md`).
- Ollama running with both models pulled:

```powershell
ollama pull qwen3-embedding:0.6b
ollama pull qwen3.5:9b
```

- Python packages installed:

```powershell
pip install openpyxl langchain-ollama langchain-qdrant
```

## 1. Ask a Single Question

- Open PowerShell, go to the project folder, and run:

```powershell
# Navigate to the folder where you cloned this repo first
cd <your-project-folder>
python chat.py "What do customers say about the kolo mee?"
```

- The answer is printed and the script exits.

## 2. Interactive Chat Mode

- Run:

```powershell
python chat.py
```

- You will see a banner, then type questions and press Enter.
- Type `exit` or `quit` to leave the chat.

## 3. Example Questions

### On-topic (Answered)

- What do customers say about the laksa?
- How is the service at the restaurant?
- What is the best time to visit ABC123 Restaurant?
- Is the restaurant good for families?

### Off-topic (Declined with a fixed refusal message)

- Who is the president of France?
- What is the weather in Kuching?

## Notes

- `chat.py` only reads from Qdrant; it does not modify the collection.
- The chat model is `qwen3.5:9b` (temperature 0.2, max 512 tokens).
- If a question is answered that should be declined (or vice versa), the assistant's strictness is controlled by the `SYSTEM_PROMPT` in `chat.py`.

## Troubleshooting

| Error                                              | Fix                                                                         |
| -------------------------------------------------- | --------------------------------------------------------------------------- |
| "Failed to initialize" / Connection refused        | Qdrant is not running; start it with: `docker start qdrant`                 |
| "model 'qwen3.5:9b' not found"                     | Pull the chat model: `ollama pull qwen3.5:9b`                               |
| "Collection restaurant_reviews doesn't exist"      | Run Step 3 first: `python embedding.py`                                     |
| Slow first answer                                  | The 9B model needs to load into memory; subsequent answers are faster.      |

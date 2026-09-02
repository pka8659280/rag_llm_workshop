# -*- coding: utf-8 -*-
"""
Chat with ABC123 Restaurant's Google reviews — the RAG (Retrieval-Augmented
Generation) part of the pipeline.

RAG in one sentence: when you ask a question, we first RETRIEVE the most
relevant reviews from Qdrant, then give those reviews to the LLM as context so
it can answer with actual review knowledge instead of guessing.

Only answers questions related to the restaurant; off-topic questions (e.g.
politics, weather) are politely declined.

Usage:
    python chat.py                        # interactive REPL (type questions, Enter to ask)
    python chat.py "question..."          # one-shot: answer a single question, then exit
"""
import os
import sys

from langchain_core.output_parsers import StrOutputParser  # takes the LLM's output and gives you plain text
from langchain_core.prompts import ChatPromptTemplate  # builds the prompt, with {placeholders} to fill in later
from langchain_ollama import ChatOllama, OllamaEmbeddings  # ChatOllama = chat LLM; OllamaEmbeddings = text -> vector
from langchain_qdrant import QdrantVectorStore  # reads the existing Qdrant collection

# --- Config ------------------------------------------------------------------
# Inside Docker (docker-compose.yml) these are overridden with the compose
# service names so the app can reach its neighbours over the compose network:
#   QDRANT_URL=http://qdrant:6333
#   OLLAMA_BASE_URL=http://ollama:11434
# When running locally (no Docker) they fall back to localhost, so nothing breaks.
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
COLLECTION_NAME = "restaurant_reviews"
EMBED_MODEL = "qwen3-embedding:0.6b"
CHAT_MODEL = "qwen3.5:9b"
TOP_K = 4  # how many similar reviews to retrieve from Qdrant per question

# Shown verbatim to the user when the question is not about the restaurant.
REFUSAL = ("I can only answer questions about ABC123 Restaurant in Kuching "
           "(food, dishes, service, prices, reviews). Please ask something related.")

# System prompt: the "rules" the LLM must follow.
# {refusal} is a placeholder — it gets replaced with the REFUSAL text above
# when the chain runs, so the wording stays consistent.
SYSTEM_PROMPT = """You are a helpful assistant for "ABC123 Restaurant" in Kuching, Malaysia.
Use the Google reviews in the context below when relevant, and you may also draw on
general knowledge about the restaurant (its food, dishes, service, prices, and ambience).
- Stay on-topic: only answer questions about the restaurant.
- If the question is NOT about the restaurant, say exactly: {refusal}
Be concise, and use the reviewer details (star rating, dish mentioned) when helpful."""

# The full prompt = a system message (rules) + a human message (the question).
# {context} and {question} are filled in by answer() later.
PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "Context:\n{context}\n\nQuestion: {question}"),
    ]
)


def format_context(results):
    """Turn the retrieved (Document, score) pairs into one readable text block.

    We include star rating / reviewer / date / dish so the LLM can reference
    real reviewer details in its answer (provenance).
    """
    parts = []
    for doc, _ in results:
        m = doc.metadata
        parts.append(
            f"[{m.get('star_rating', '?')}*] {m.get('reviewer_name', '')} "
            f"({m.get('review_date', '')}) - dish: {m.get('dish_mentioned', '-')}\n"
            f"{doc.page_content}"
        )
    return "\n\n".join(parts)


def build():
    """Create the vector store (reads the existing Qdrant collection) and the chat LLM."""
    try:
        # IMPORTANT: this embedding model MUST match the one used in embedding.py.
        # Similarity only makes sense if the question and the reviews were embedded
        # with the same model (same "language" of numbers).
        # base_url points at the Ollama server; in Docker it is the service name.
        embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL)
        # The collection was already created by embedding.py, so we just open it.
        store = QdrantVectorStore.from_existing_collection(
            collection_name=COLLECTION_NAME,
            embedding=embeddings,
            url=QDRANT_URL,
        )
        # ChatOllama = the actual "brain". temperature=0.2 keeps answers fairly
        # focused; num_predict=512 caps the answer length; reasoning=False skips
        # the thinking step so answers come back faster.
        llm = ChatOllama(
            model=CHAT_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.2,
            num_predict=512,
            reasoning=False,
        )
        return store, llm
    except Exception as e:
        # Fail fast with a helpful message instead of crashing later on.
        print(f"Failed to initialize: {e}")
        print("Check that Qdrant is running on port 6333 and the model is pulled (ollama list).")
        sys.exit(1)


def answer(store, llm, question):
    """Return an answer for a restaurant-related question (the RAG retrieval + generation)."""
    # 1) RETRIEVE: embed the question and ask Qdrant for the TOP_K closest review
    #    vectors. similarity_search_with_score returns (Document, score) pairs —
    #    the reviews are context for the LLM, not a hard limit on what it can say.
    results = store.similarity_search_with_score(question, k=TOP_K)
    # 2) GENERATE: the pipe "|" chains prompt -> llm -> text parser into one call.
    chain = PROMPT | llm | StrOutputParser()
    #    invoke() fills the {context}, {question} and {refusal} placeholders.
    return chain.invoke({"context": format_context(results), "question": question, "refusal": REFUSAL})


def main():
    store, llm = build()

    if len(sys.argv) > 1:  # one-shot mode: "python chat.py <question>"
        print(answer(store, llm, " ".join(sys.argv[1:])))
        return

    # Interactive REPL mode: keep asking until the user types exit/quit.
    print("Chat with ABC123 Restaurant reviews (Qdrant RAG). Type 'exit' or 'quit' to leave.")
    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):  # Ctrl+D or Ctrl+C -> quit politely
            print()
            break
        if not question:
            continue
        if question.lower() in ("exit", "quit"):
            break
        print("Bot:", answer(store, llm, question))


if __name__ == "__main__":
    main()

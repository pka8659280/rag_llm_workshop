# -*- coding: utf-8 -*-
"""
Chat with ABC123 Restaurant's Google reviews (RAG) — LangChain only.

- Retrieves relevant reviews from Qdrant ("restaurant_reviews").
- Only answers questions related to the restaurant; unrelated questions are declined.

Usage:
    python chat.py                        # interactive REPL
    python chat.py "question..."          # single question, then exit
"""
import sys

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore

QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "restaurant_reviews"
EMBED_MODEL = "qwen3-embedding:0.6b"
CHAT_MODEL = "qwen3.5:9b"
TOP_K = 4

REFUSAL = ("I can only answer questions about ABC123 Restaurant in Kuching "
           "(food, dishes, service, prices, reviews). Please ask something related.")

SYSTEM_PROMPT = """You are a helpful assistant for "ABC123 Restaurant" in Kuching, Malaysia.
Use the Google reviews in the context below when relevant, and you may also draw on
general knowledge about the restaurant (its food, dishes, service, prices, and ambience).
- Stay on-topic: only answer questions about the restaurant.
- If the question is NOT about the restaurant, say exactly: {refusal}
Be concise, and use the reviewer details (star rating, dish mentioned) when helpful."""

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "Context:\n{context}\n\nQuestion: {question}"),
    ]
)


def format_context(hits):
    """Format retrieved (Document, score) pairs into a readable context block."""
    parts = []
    for doc, _ in hits:
        m = doc.metadata
        parts.append(
            f"[{m.get('star_rating', '?')}*] {m.get('reviewer_name', '')} "
            f"({m.get('review_date', '')}) - dish: {m.get('dish_mentioned', '-')}\n"
            f"{doc.page_content}"
        )
    return "\n\n".join(parts)


def build():
    """Create the vector store (existing Qdrant collection) and the chat LLM."""
    try:
        embeddings = OllamaEmbeddings(model=EMBED_MODEL)
        store = QdrantVectorStore.from_existing_collection(
            collection_name=COLLECTION_NAME,
            embedding=embeddings,
            url=QDRANT_URL,
        )
        llm = ChatOllama(model=CHAT_MODEL, temperature=0.2, num_predict=512, reasoning=False)
        return store, llm
    except Exception as e:
        print(f"Failed to initialize: {e}")
        print("Check that Qdrant is running on port 6333 and the model is pulled (ollama list).")
        sys.exit(1)


def answer(store, llm, question):
    """Return an answer for a restaurant-related question."""
    hits = store.similarity_search_with_score(question, k=TOP_K)  # reviews as context, not a hard limit
    chain = PROMPT | llm | StrOutputParser()
    return chain.invoke({"context": format_context(hits), "question": question, "refusal": REFUSAL})


def main():
    store, llm = build()

    if len(sys.argv) > 1:  # one-shot mode
        print(answer(store, llm, " ".join(sys.argv[1:])))
        return

    print("Chat with ABC123 Restaurant reviews (Qdrant RAG). Type 'exit' or 'quit' to leave.")
    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question:
            continue
        if question.lower() in ("exit", "quit"):
            break
        print("Bot:", answer(store, llm, question))


if __name__ == "__main__":
    main()

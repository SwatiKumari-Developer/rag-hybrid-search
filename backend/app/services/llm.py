"""
LLM SERVICE
-----------
Uses Anthropic's Claude API to generate context-aware answers
from retrieved document chunks.

RAG PATTERN:
  1. Retrieved chunks = "Context"
  2. User question = "Query"
  3. Prompt = Context + Query → Claude generates grounded answer

WHY CLAUDE FOR GENERATION?
  - Strong instruction following and long-context reasoning
  - Avoids hallucination by grounding to provided context
  - Returns honest "I don't know" when context is insufficient
  - Fast inference via Haiku model (cost-efficient for RAG)

PROMPT ENGINEERING STRATEGY:
  - System prompt defines the RAG assistant persona and constraints
  - Context chunks are numbered and attributed to source documents
  - Model is explicitly told NOT to use outside knowledge
  - Encourages citing which document(s) the answer comes from
"""

from typing import List, Dict, Any, AsyncGenerator
import anthropic
from loguru import logger

from app.core.config import settings


# Lazy client initialization
_client: anthropic.Anthropic | None = None


def get_anthropic_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is not set in environment")
        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


def build_context_prompt(chunks: List[Dict[str, Any]]) -> str:
    """
    Format retrieved chunks into a structured context block for the LLM.
    Each chunk is numbered and attributed to its source document.
    """
    if not chunks:
        return "No relevant documents were found."

    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        title = chunk.get("title") or chunk.get("filename", "Unknown Document")
        method = chunk.get("retrieval_method", "hybrid")
        score = chunk.get("rrf_score", 0)
        context_parts.append(
            f"[Document {i}: {title} | Retrieved by: {method} search | Score: {score:.4f}]\n"
            f"{chunk['text']}\n"
        )

    return "\n---\n".join(context_parts)


SYSTEM_PROMPT = """You are an intelligent document assistant for a RAG (Retrieval-Augmented Generation) system.

Your job is to answer user questions based STRICTLY on the provided document context.

RULES:
1. Only use information from the provided context. Do not use prior knowledge.
2. If the context doesn't contain enough information to answer, clearly say so.
3. Always cite which document(s) your answer comes from (e.g. "According to Document 2...").
4. Be concise but complete. Use bullet points for lists.
5. If multiple documents have conflicting information, mention the conflict.
6. Never make up facts, URLs, names, or statistics not present in the context.

FORMAT:
- Start with a direct answer to the question.
- Follow with supporting details from the context.
- End with a brief note on which documents were most useful."""


def generate_answer(
    query: str,
    chunks: List[Dict[str, Any]],
    conversation_history: List[Dict] = None,
) -> Dict[str, Any]:
    """
    Generate a context-grounded answer using Claude.

    Args:
        query: The user's question
        chunks: Retrieved document chunks (from hybrid search)
        conversation_history: Optional previous Q&A turns (for multi-turn)

    Returns:
        Dict with answer text and metadata
    """
    client = get_anthropic_client()
    context = build_context_prompt(chunks)

    # Build the user message with context embedded
    user_message = f"""DOCUMENT CONTEXT:
{context}

QUESTION: {query}

Please answer the question based on the document context above."""

    # Build messages list (support multi-turn conversation)
    messages = []
    if conversation_history:
        messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})

    logger.info(f"Calling Claude ({settings.LLM_MODEL}) with {len(chunks)} context chunks")

    try:
        response = client.messages.create(
            model=settings.LLM_MODEL,
            max_tokens=settings.MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=messages,
        )

        answer_text = response.content[0].text

        return {
            "answer": answer_text,
            "model": settings.LLM_MODEL,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "sources": [
                {
                    "document_id": c.get("document_id"),
                    "filename": c.get("filename"),
                    "title": c.get("title"),
                    "chunk_index": c.get("chunk_index"),
                    "retrieval_method": c.get("retrieval_method"),
                    "rrf_score": round(c.get("rrf_score", 0), 6),
                }
                for c in chunks
            ],
        }

    except anthropic.APIError as e:
        logger.error(f"Anthropic API error: {e}")
        raise RuntimeError(f"LLM generation failed: {str(e)}")


def generate_answer_streaming(
    query: str,
    chunks: List[Dict[str, Any]],
) -> AsyncGenerator[str, None]:
    """
    Streaming version — yields text tokens as they're generated.
    Use with SSE (Server-Sent Events) for real-time UI updates.
    (Implemented as a sync generator for simplicity; adapt for async as needed.)
    """
    client = get_anthropic_client()
    context = build_context_prompt(chunks)

    user_message = f"""DOCUMENT CONTEXT:
{context}

QUESTION: {query}"""

    with client.messages.stream(
        model=settings.LLM_MODEL,
        max_tokens=settings.MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        for text in stream.text_stream:
            yield text

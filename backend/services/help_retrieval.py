"""
RAG retrieval service for help corpus.

Responsible for:
- Embedding user queries via OpenAI text-embedding-3-small (or mock in dev)
- Running pgvector cosine similarity search with audience filtering
- Returning top-K chunks with metadata

B16/A85 — Established in Batch B16.
"""

import logging
from typing import Any

from sqlalchemy import text
from sqlmodel import Session

from core.config import settings

logger = logging.getLogger(__name__)


def retrieve_chunks(
    db: Session,
    query_text: str,
    user_role: str,
    category_hint: str | None = None,
    k: int = 5,
) -> list[dict[str, Any]]:
    """
    Embed the query and retrieve the most relevant help article chunks.

    Args:
        db:             Active database session.
        query_text:     The user's question text. Will be embedded via OpenAI API.
        user_role:      Requesting user's role ('owner' | 'accountant' | 'technician').
                        Used to filter chunks to audience-appropriate articles only.
        category_hint:  Optional category slug to narrow the search (e.g. 'integrations').
                        If None, searches across all categories.
        k:              Number of top chunks to return. Default 5.

    Returns:
        List of up to k chunk dicts, ordered by descending cosine similarity score.
        Each dict contains: chunk_id, article_id, section_title, chunk_text, score.

    Raises:
        httpx.HTTPError: If the OpenAI embedding API call fails.
    """
    embedding = _embed_query(query_text)
    embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

    # Build the pgvector cosine similarity query with audience filtering
    # audience @> ARRAY[role] checks if the article targets this user's role
    if category_hint:
        sql = text("""
            SELECT
                c.chunk_id::text,
                c.article_id,  -- FK child column, stays article_id (FIND-169)
                c.section_title,
                c.chunk_text,
                1 - (c.embedding <=> :embedding::vector) AS score
            FROM help_article_chunk c
            JOIN help_article a ON c.article_id = a.code
            WHERE a.audience @> ARRAY[:role]::text[]
              AND a.category = :category
            ORDER BY c.embedding <=> :embedding::vector
            LIMIT :k
        """)
        rows = db.exec(
            sql,
            params={
                "embedding": embedding_str,
                "role": user_role,
                "category": category_hint,
                "k": k,
            },
        ).all()
    else:
        sql = text("""
            SELECT
                c.chunk_id::text,
                c.article_id,  -- FK child column, stays article_id (FIND-169)
                c.section_title,
                c.chunk_text,
                1 - (c.embedding <=> :embedding::vector) AS score
            FROM help_article_chunk c
            JOIN help_article a ON c.article_id = a.code
            WHERE a.audience @> ARRAY[:role]::text[]
            ORDER BY c.embedding <=> :embedding::vector
            LIMIT :k
        """)
        rows = db.exec(
            sql,
            params={
                "embedding": embedding_str,
                "role": user_role,
                "k": k,
            },
        ).all()

    return [
        {
            "chunk_id": row[0],
            "article_id": row[1],
            "section_title": row[2],
            "chunk_text": row[3],
            "score": float(row[4]),
        }
        for row in rows
    ]


def _embed_query(query_text: str) -> list[float]:
    """
    Embed a query string via OpenAI text-embedding-3-small.
    Returns a 1536-dimensional vector.

    In dev/test when OPENAI_API_KEY is unset, returns all-zeros vector.
    Callers should check for zero-vector if they need to distinguish real from mock.
    """

    if not settings.OPENAI_API_KEY:
        logger.debug(
            "OPENAI_API_KEY not set — returning zero-vector for query embedding (dev/test mode)"
        )
        return [0.0] * 1536

    try:
        import httpx

        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "input": query_text,
                    "model": "text-embedding-3-small",
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
    except Exception as e:
        logger.error(f"OpenAI embedding API error: {e}")
        raise

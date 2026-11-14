"""
Help corpus management service.

Responsible for:
- Fetching and parsing article markdown from S3
- Chunking at section boundaries
- Delegating embedding to help_retrieval
- Upserting chunks in pgvector

B16/A85 — Established in Batch B16.
"""

import hashlib
import logging
import re
from datetime import UTC, date, datetime
from typing import Any

from sqlmodel import Session, select

from core.config import settings

logger = logging.getLogger(__name__)

# Token estimation: ~4 chars per token (rough approximation without tiktoken dep)
_CHARS_PER_TOKEN = 4
_MIN_CHUNK_TOKENS = 100
_MAX_CHUNK_TOKENS = 800


def process_article(
    article_id: str,
    s3_path: str,
    db: Session,
) -> dict:
    """
    Full pipeline: fetch → parse → chunk → hash-check → embed → store.

    Called by the process_help_article Celery task.

    Args:
        article_id:  Article slug matching help_article.article_id.
        s3_path:     Full S3 path of the markdown file.
        db:          Active database session.

    Returns:
        Dict with keys: article_id, chunks_embedded, chunks_skipped, hash_unchanged (bool).

    Raises:
        ValueError:        If frontmatter is missing required fields.
        botocore.exceptions.BotoCoreError: If S3 read fails (propagates for Celery retry).
        httpx.HTTPError:   If OpenAI embedding API fails (propagates for Celery retry).
    """

    # Guard: skip processing if S3 bucket not configured
    if not settings.HELP_CONTENT_BUCKET:
        logger.warning(
            f"HELP_CONTENT_BUCKET not set — skipping article {article_id} (dev mode)"
        )
        return {
            "article_id": article_id,
            "status": "skipped_no_bucket",
            "chunks_embedded": 0,
            "chunks_skipped": 0,
            "hash_unchanged": False,
        }

    # Guard: skip processing if OpenAI key not configured
    if not settings.OPENAI_API_KEY:
        logger.warning(
            f"OPENAI_API_KEY not set — skipping article {article_id} (dev mode)"
        )
        return {
            "article_id": article_id,
            "status": "skipped_no_api_key",
            "chunks_embedded": 0,
            "chunks_skipped": 0,
            "hash_unchanged": False,
        }

    # Fetch markdown from S3
    content = _fetch_from_s3(s3_path)

    # Parse frontmatter
    frontmatter, body = _parse_frontmatter(content, article_id)

    # Hash-check to avoid re-embedding unchanged content
    content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()

    from app.models.help import HelpArticle, HelpArticleChunk

    # FIND-169: article_id → code on HelpArticle
    existing = db.exec(
        select(HelpArticle).where(HelpArticle.code == article_id)
    ).first()

    if existing and existing.last_content_hash == content_hash:
        logger.info(f"Article {article_id} content unchanged — skipping re-embedding")
        return {
            "article_id": article_id,
            "status": "ok",
            "chunks_embedded": 0,
            "chunks_skipped": 0,
            "hash_unchanged": True,
        }

    # Chunk the article
    chunks = chunk_article(body, frontmatter, article_id)

    # Embed each chunk and upsert
    from services.help_retrieval import _embed_query

    now_utc = datetime.now(UTC)
    chunks_embedded = 0

    # Delete existing chunks for this article (replace-all strategy)
    if existing:
        # child column article_id still references help_article.code (FIND-169)
        db.exec(
            select(HelpArticleChunk).where(HelpArticleChunk.article_id == article_id)
        )
        # Use raw SQL delete for efficiency
        from sqlalchemy import text as sa_text

        db.exec(
            sa_text("DELETE FROM help_article_chunk WHERE article_id = :aid"),
            params={"aid": article_id},
        )

    # Upsert article record
    article_data = {
        "s3_path": s3_path,
        "title": frontmatter.get("title", article_id),
        "category": frontmatter.get("category", "general"),
        "frontmatter_metadata": frontmatter,
        "last_content_hash": content_hash,
        "last_processed_at": now_utc,
        "last_updated": _parse_last_updated(frontmatter),
        "audience": frontmatter.get("audience", ["owner"]),
        "created_at": now_utc,
    }

    if existing:
        for k, v in article_data.items():
            if k != "created_at":
                setattr(existing, k, v)
        db.add(existing)
    else:
        article_obj = HelpArticle(article_id=article_id, **article_data)
        db.add(article_obj)

    db.flush()  # ensure article exists before inserting chunks

    # Insert chunks with embeddings
    for chunk in chunks:
        embedding = _embed_query(chunk["chunk_text_with_metadata"])
        chunk_obj = HelpArticleChunk(
            article_id=article_id,
            chunk_order=chunk["chunk_order"],
            section_title=chunk["section_title"],
            chunk_text=chunk["chunk_text"],
            chunk_text_with_metadata=chunk["chunk_text_with_metadata"],
            embedding=embedding,
            token_count=chunk["token_count"],
            created_at=now_utc,
        )
        db.add(chunk_obj)
        chunks_embedded += 1

    db.commit()

    # Ensure HNSW index exists (create after first row — design doc requirement)
    _ensure_hnsw_index(db)

    logger.info(f"Article {article_id}: embedded {chunks_embedded} chunks")
    return {
        "article_id": article_id,
        "status": "ok",
        "chunks_embedded": chunks_embedded,
        "chunks_skipped": 0,
        "hash_unchanged": False,
    }


def chunk_article(
    markdown_content: str,
    frontmatter: dict,
    article_id: str,
) -> list[dict]:
    """
    Split markdown into chunks at ## section boundaries.

    Rules:
    - Minimum chunk size: 100 tokens (short sections merged with next)
    - Maximum chunk size: 800 tokens (long sections split at paragraph boundaries)
    - Each chunk's chunk_text_with_metadata prepends article frontmatter as context header

    Returns:
        List of chunk dicts with: chunk_order, section_title, chunk_text,
        chunk_text_with_metadata, token_count.
    """
    # Build context header from frontmatter for prepending
    context_header = _build_context_header(frontmatter, article_id)

    # Split by ## headings
    raw_sections = re.split(r"\n(?=## )", markdown_content.strip())

    # Build initial sections list
    sections: list[tuple[str, str]] = []  # (heading, body)
    for section in raw_sections:
        lines = section.strip().split("\n", 1)
        heading = lines[0].strip().lstrip("#").strip() if lines else "Introduction"
        body = lines[1].strip() if len(lines) > 1 else ""
        sections.append((heading, body))

    # Merge short sections and split long ones
    merged: list[tuple[str, str]] = []
    pending_heading: str | None = None
    pending_body = ""

    for heading, body in sections:
        combined = (pending_body + "\n\n" + body).strip() if pending_heading else body
        combined_tokens = len(combined) // _CHARS_PER_TOKEN

        if pending_heading is None:
            pending_heading = heading
            pending_body = body
        elif combined_tokens < _MIN_CHUNK_TOKENS:
            # Merge with previous (too short on its own)
            pending_body = combined
        else:
            merged.append((pending_heading, pending_body))
            pending_heading = heading
            pending_body = body

    if pending_heading is not None:
        merged.append((pending_heading, pending_body))

    # Build final chunks (splitting oversized sections)
    chunks = []
    chunk_order = 0

    for heading, body in merged:
        token_count = len(body) // _CHARS_PER_TOKEN

        if token_count <= _MAX_CHUNK_TOKENS:
            chunk_text_with_metadata = f"{context_header}\n\n## {heading}\n\n{body}"
            chunks.append(
                {
                    "chunk_order": chunk_order,
                    "section_title": heading,
                    "chunk_text": body,
                    "chunk_text_with_metadata": chunk_text_with_metadata,
                    "token_count": len(chunk_text_with_metadata) // _CHARS_PER_TOKEN,
                }
            )
            chunk_order += 1
        else:
            # Split long section at paragraph boundaries
            paragraphs = body.split("\n\n")
            sub_body = ""
            for para in paragraphs:
                candidate = (sub_body + "\n\n" + para).strip() if sub_body else para
                if len(candidate) // _CHARS_PER_TOKEN > _MAX_CHUNK_TOKENS and sub_body:
                    chunk_text_with_metadata = (
                        f"{context_header}\n\n## {heading}\n\n{sub_body}"
                    )
                    chunks.append(
                        {
                            "chunk_order": chunk_order,
                            "section_title": heading,
                            "chunk_text": sub_body,
                            "chunk_text_with_metadata": chunk_text_with_metadata,
                            "token_count": len(chunk_text_with_metadata)
                            // _CHARS_PER_TOKEN,
                        }
                    )
                    chunk_order += 1
                    sub_body = para
                else:
                    sub_body = candidate

            if sub_body:
                chunk_text_with_metadata = (
                    f"{context_header}\n\n## {heading}\n\n{sub_body}"
                )
                chunks.append(
                    {
                        "chunk_order": chunk_order,
                        "section_title": heading,
                        "chunk_text": sub_body,
                        "chunk_text_with_metadata": chunk_text_with_metadata,
                        "token_count": len(chunk_text_with_metadata)
                        // _CHARS_PER_TOKEN,
                    }
                )
                chunk_order += 1

    return chunks


# ──────────────────────────────────────────────────────────────────────────────
# Private helpers
# ──────────────────────────────────────────────────────────────────────────────


def _fetch_from_s3(s3_path: str) -> str:
    """Fetch markdown content from S3. Raises botocore exceptions on failure."""
    import boto3  # type: ignore

    # s3_path format: s3://bucket/key
    without_prefix = s3_path.removeprefix("s3://")
    bucket, _, key = without_prefix.partition("/")

    s3 = boto3.client("s3")
    response = s3.get_object(Bucket=bucket, Key=key)
    return response["Body"].read().decode("utf-8")


def _parse_frontmatter(content: str, article_id: str) -> tuple[dict, str]:
    """
    Parse YAML frontmatter from markdown content.
    Returns (frontmatter_dict, body_markdown).
    Raises ValueError if required fields are missing.
    """
    if not content.startswith("---"):
        # No frontmatter — treat whole content as body
        return {
            "title": article_id,
            "category": "general",
            "audience": ["owner"],
        }, content

    end = content.find("\n---", 3)
    if end == -1:
        return {
            "title": article_id,
            "category": "general",
            "audience": ["owner"],
        }, content

    fm_block = content[3:end].strip()
    body = content[end + 4 :].strip()

    # Simple YAML-like parser (avoid pyyaml dep)
    frontmatter: dict[str, Any] = {}
    for line in fm_block.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            frontmatter[k.strip()] = v.strip().strip("\"'")

    required = {"title", "category"}
    missing = required - set(frontmatter.keys())
    if missing:
        raise ValueError(
            f"Article {article_id} frontmatter missing required fields: {missing}"
        )

    # Parse audience as list
    audience_raw = frontmatter.get("audience", "owner")
    if isinstance(audience_raw, str):
        frontmatter["audience"] = [a.strip() for a in audience_raw.split(",")]

    return frontmatter, body


def _parse_last_updated(frontmatter: dict) -> date:
    """Parse last_updated date from frontmatter or fallback to today."""
    raw = frontmatter.get("last_updated", "")
    try:
        return date.fromisoformat(str(raw))
    except (ValueError, TypeError):
        return date.today()


def _build_context_header(frontmatter: dict, article_id: str) -> str:
    """Build a compact context header to prepend to each chunk embedding."""
    title = frontmatter.get("title", article_id)
    category = frontmatter.get("category", "general")
    audience = frontmatter.get("audience", ["owner"])
    if isinstance(audience, list):
        audience_str = ", ".join(audience)
    else:
        audience_str = str(audience)
    return f"Article: {title}\nCategory: {category}\nAudience: {audience_str}"


def _ensure_hnsw_index(db: Session) -> None:
    """
    Create HNSW index on embedding column if it doesn't already exist.
    Called after first chunk is inserted — required by design doc §A.
    """
    from sqlalchemy import text as sa_text

    try:
        db.exec(
            sa_text("""
            CREATE INDEX IF NOT EXISTS help_article_chunk_embedding_hnsw_idx
            ON public.help_article_chunk USING hnsw (embedding vector_cosine_ops)
        """)
        )
        db.commit()
    except Exception as e:
        logger.warning(f"Could not create HNSW index (may already exist): {e}")
        db.rollback()

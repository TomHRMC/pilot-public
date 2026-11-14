"""
A85 — Corpus & Embedding Pipeline tests.

Test focus:
- chunk_article() splits correctly at ## boundaries
- Short sections merge, long sections split
- process_article() skips when no API key / no bucket
- _embed_query() returns zero-vector when OPENAI_API_KEY not set
- HelpArticle and HelpArticleChunk ORM models create/read correctly
"""

from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

# ──────────────────────────────────────────────────────────────────────────────
# ORM model smoke tests
# ──────────────────────────────────────────────────────────────────────────────


class TestHelpArticleModel:
    def test_help_article_create(self, db_session, test_tenant):
        from app.models.help import HelpArticle

        # FIND-169: article_id → code on HelpArticle
        article = HelpArticle(
            code="test-article-1",
            s3_path="s3://pilot-help-content/en/integrations/test-article-1.md",
            title="Test Article",
            category="integrations",
            frontmatter_metadata={"title": "Test Article", "category": "integrations"},
            last_content_hash="abc123",
            last_processed_at=datetime.now(UTC),
            last_updated=date.today(),
            audience=["owner", "accountant"],
            created_at=datetime.now(UTC),
        )
        db_session.add(article)
        db_session.commit()
        db_session.refresh(article)

        # FIND-169: article_id → code on HelpArticle
        assert article.code == "test-article-1"
        assert article.category == "integrations"
        assert "owner" in article.audience

    def test_help_article_chunk_create(self, db_session, test_tenant):
        from app.models.help import HelpArticle, HelpArticleChunk

        now_utc = datetime.now(UTC)
        # FIND-169: article_id → code on HelpArticle
        article = HelpArticle(
            code="test-article-chunk",
            s3_path="s3://pilot-help-content/en/integrations/test.md",
            title="Test Article",
            category="integrations",
            frontmatter_metadata={},
            last_content_hash="xyz",
            last_processed_at=now_utc,
            last_updated=date.today(),
            audience=["owner"],
            created_at=now_utc,
        )
        db_session.add(article)
        db_session.flush()

        chunk = HelpArticleChunk(
            article_id="test-article-chunk",
            chunk_order=0,
            section_title="Introduction",
            chunk_text="This is the introduction content.",
            chunk_text_with_metadata="Article: Test\n\nThis is the introduction content.",
            embedding=[0.0] * 1536,
            token_count=10,
            created_at=now_utc,
        )
        db_session.add(chunk)
        db_session.commit()
        db_session.refresh(chunk)

        assert chunk.article_id == "test-article-chunk"
        assert chunk.chunk_order == 0
        assert chunk.token_count == 10


# ──────────────────────────────────────────────────────────────────────────────
# Chunking logic tests
# ──────────────────────────────────────────────────────────────────────────────


class TestChunkArticle:
    def test_basic_chunking(self):
        from services.help_corpus import chunk_article

        content = """## Introduction

        This is the introduction to QuickBooks integration.

        ## Connecting Your Account

        To connect your account, go to Settings and click Connect.
        Follow the OAuth flow to authorize Pilot.

        ## Troubleshooting

        If you see an error, try disconnecting and reconnecting.
        """
        frontmatter = {
            "title": "QuickBooks Integration",
            "category": "integrations",
            "audience": ["owner"],
        }
        chunks = chunk_article(content, frontmatter, "quickbooks-integration")

        assert len(chunks) >= 1
        for chunk in chunks:
            assert "chunk_order" in chunk
            assert "section_title" in chunk
            assert "chunk_text" in chunk
            assert "chunk_text_with_metadata" in chunk
            assert "token_count" in chunk

    def test_chunk_order_is_sequential(self):
        from services.help_corpus import chunk_article

        content = "\n".join(
            [f"## Section {i}\n\n{'Content for section. ' * 20}" for i in range(5)]
        )
        frontmatter = {"title": "Test", "category": "general", "audience": ["owner"]}
        chunks = chunk_article(content, frontmatter, "test-article")

        orders = [c["chunk_order"] for c in chunks]
        assert orders == sorted(orders)
        assert len(set(orders)) == len(orders)  # no duplicate orders

    def test_context_header_prepended(self):
        from services.help_corpus import chunk_article

        content = "## Overview\n\nSome overview content here for testing."
        frontmatter = {
            "title": "My Article",
            "category": "billing",
            "audience": ["owner", "accountant"],
        }
        chunks = chunk_article(content, frontmatter, "my-article")

        assert len(chunks) >= 1
        metadata_text = chunks[0]["chunk_text_with_metadata"]
        assert "My Article" in metadata_text
        assert "billing" in metadata_text

    def test_empty_content_handled(self):
        from services.help_corpus import chunk_article

        content = ""
        frontmatter = {"title": "Empty", "category": "general", "audience": ["owner"]}
        chunks = chunk_article(content, frontmatter, "empty")
        # Should not raise, may return empty list
        assert isinstance(chunks, list)


# ──────────────────────────────────────────────────────────────────────────────
# Embedding mock tests
# ──────────────────────────────────────────────────────────────────────────────


class TestEmbedQuery:
    def test_returns_zero_vector_when_no_api_key(self):
        from services.help_retrieval import _embed_query

        with patch("services.help_retrieval.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = ""
            result = _embed_query("test query")

        assert len(result) == 1536
        assert all(v == 0.0 for v in result)

    def test_calls_openai_when_key_present(self):
        from services.help_retrieval import _embed_query

        mock_embedding = [0.1] * 1536
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": [{"embedding": mock_embedding}]}
        mock_resp.raise_for_status = MagicMock()

        # Production code uses: with httpx.Client(timeout=...) as client: client.post(...)
        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_client)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("services.help_retrieval.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "sk-test123"
            with patch("httpx.Client", return_value=mock_cm):
                result = _embed_query("How do I connect QuickBooks?")

        assert result == mock_embedding
        assert len(result) == 1536


# ──────────────────────────────────────────────────────────────────────────────
# process_article skipping tests
# ──────────────────────────────────────────────────────────────────────────────


class TestProcessArticleSkipping:
    def test_skips_when_no_bucket(self, db_session):
        from services.help_corpus import process_article

        with patch("services.help_corpus.settings") as mock_settings:
            mock_settings.HELP_CONTENT_BUCKET = ""
            mock_settings.OPENAI_API_KEY = "sk-test"
            result = process_article("test-article", "s3://bucket/key.md", db_session)

        assert result["status"] == "skipped_no_bucket"

    def test_skips_when_no_api_key(self, db_session):
        from services.help_corpus import process_article

        with patch("services.help_corpus.settings") as mock_settings:
            mock_settings.HELP_CONTENT_BUCKET = "pilot-help-content"
            mock_settings.OPENAI_API_KEY = ""
            result = process_article("test-article", "s3://bucket/key.md", db_session)

        assert result["status"] == "skipped_no_api_key"


# ──────────────────────────────────────────────────────────────────────────────
# Celery task impl tests
# ──────────────────────────────────────────────────────────────────────────────


class TestProcessHelpArticleTask:
    def test_impl_calls_process_article(self, db_session):
        from tasks.help_corpus import _process_help_article_impl

        with patch("tasks.help_corpus.process_article") as mock_process:
            mock_process.return_value = {
                "article_id": "test",
                "status": "ok",
                "chunks_embedded": 3,
            }
            result = _process_help_article_impl(
                "test-article", "s3://bucket/test.md", db_session
            )

        mock_process.assert_called_once_with(
            article_id="test-article",
            s3_path="s3://bucket/test.md",
            db=db_session,
        )
        assert result["chunks_embedded"] == 3

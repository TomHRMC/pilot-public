"""
FIND-124 (S2 High) — HNSW index on help_article_chunk.embedding for ANN search.

Without this index, every RAG help query (finding semantically similar NEC chunks)
does a full sequential scan. With HNSW: approximate nearest-neighbor in O(log n).

Migration: phase_fe_1_batch_b18_help_article_chunk_hnsw_index (95c8acb7be77)

Test coverage:
  1. DB: index ix_help_article_chunk_embedding_hnsw exists
  2. DB: index uses HNSW access method (not btree/hash)
  3. DB: index uses vector_cosine_ops operator class

Test subfolder: tests/batch_b18/
"""


class TestFind124HnswIndexExists:
    """HNSW index must exist on help_article_chunk.embedding after FIND-124 migration."""

    def test_hnsw_index_exists(self, db_session):
        """ix_help_article_chunk_embedding_hnsw must exist in pg_indexes."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename = 'help_article_chunk' "
                "  AND indexname = 'ix_help_article_chunk_embedding_hnsw'"
            )
        ).first()

        assert result is not None, (
            "Index 'ix_help_article_chunk_embedding_hnsw' missing from help_article_chunk — "
            "FIND-124 migration not applied"
        )


class TestFind124HnswAccessMethod:
    """HNSW index must use the 'hnsw' access method (not btree or hash)."""

    def test_index_uses_hnsw_access_method(self, db_session):
        """Index access method must be 'hnsw' — not btree or hash."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT am.amname "
                "FROM pg_indexes ix "
                "JOIN pg_class c ON c.relname = ix.indexname "
                "JOIN pg_am am ON am.oid = c.relam "
                "WHERE ix.tablename = 'help_article_chunk' "
                "  AND ix.indexname = 'ix_help_article_chunk_embedding_hnsw'"
            )
        ).first()

        assert result is not None, (
            "Could not retrieve access method for ix_help_article_chunk_embedding_hnsw"
        )
        assert result[0] == "hnsw", (
            f"Index access method must be 'hnsw', got '{result[0]}' — "
            "HNSW index not created correctly"
        )


class TestFind124HnswOperatorClass:
    """HNSW index must use vector_cosine_ops operator class for cosine similarity."""

    def test_index_uses_vector_cosine_ops(self, db_session):
        """Index must use vector_cosine_ops (cosine distance for RAG similarity search)."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT ix.indexdef "
                "FROM pg_indexes ix "
                "WHERE ix.tablename = 'help_article_chunk' "
                "  AND ix.indexname = 'ix_help_article_chunk_embedding_hnsw'"
            )
        ).first()

        assert result is not None, (
            "ix_help_article_chunk_embedding_hnsw index definition not found"
        )
        index_def = result[0].lower()
        assert "vector_cosine_ops" in index_def, (
            f"Index must use vector_cosine_ops operator class, got definition: {index_def}"
        )
        assert "hnsw" in index_def, (
            f"Index definition must reference hnsw, got: {index_def}"
        )

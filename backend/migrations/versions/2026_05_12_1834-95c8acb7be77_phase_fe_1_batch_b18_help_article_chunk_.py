"""phase_fe_1_batch_b18_help_article_chunk_hnsw_index

FIND-124 (S2 High) — Add HNSW index on help_article_chunk.embedding for ANN search.

Without this index, every RAG help query does a full sequential scan of all embedding
rows. With HNSW, approximate nearest-neighbor search is O(log n).

Index settings:
  m=16          — bidirectional links per node (balanced accuracy/speed)
  ef_construction=64 — candidate list size during build

Revision ID: 95c8acb7be77
Revises: d4f05609e2a5
Create Date: 2026-05-12 18:34:29.220631+00:00
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "95c8acb7be77"
down_revision: str | None = "d4f05609e2a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX ix_help_article_chunk_embedding_hnsw
          ON help_article_chunk
          USING hnsw (embedding vector_cosine_ops)
          WITH (m=16, ef_construction=64)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_help_article_chunk_embedding_hnsw")

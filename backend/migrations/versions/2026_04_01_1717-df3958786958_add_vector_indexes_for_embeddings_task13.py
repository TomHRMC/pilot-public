"""add_vector_indexes_for_embeddings_task13

Revision ID: df3958786958
Revises: 0a79f3e208e1
Create Date: 2026-04-01 17:17:47.930017+00:00

"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "df3958786958"
down_revision: str | None = "0a79f3e208e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create HNSW indexes for vector similarity search on conversation embeddings."""

    # Get the connection
    connection = op.get_bind()

    # Ensure pgvector extension is enabled (should already exist, but defensive)
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

    # CONCURRENTLY requires running outside a transaction block
    # Commit any pending transaction and disable autocommit
    connection.execute(text("COMMIT;"))

    # Create HNSW index for conversation_session.context_embedding
    # CONCURRENTLY ensures no table lock during index build (production safe)
    # m=16: Number of connections per node in HNSW graph (higher = more accurate, slower build)
    # ef_construction=64: Search quality during build (higher = better recall, slower build)
    # vector_cosine_ops: Use cosine distance for similarity (normalized dot product)
    connection.execute(
        text("""
        CREATE INDEX CONCURRENTLY idx_conv_session_context_embedding 
        ON conversation_session 
        USING hnsw (context_embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
    """)
    )

    # Create HNSW index for conversation_message.embedding
    connection.execute(
        text("""
        CREATE INDEX CONCURRENTLY idx_conv_msg_embedding 
        ON conversation_message 
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
    """)
    )


def downgrade() -> None:
    """Remove HNSW indexes for vector similarity search."""

    # Drop HNSW indexes (CONCURRENTLY not needed for DROP)
    connection = op.get_bind()
    connection.execute(text("DROP INDEX IF EXISTS idx_conv_msg_embedding;"))
    connection.execute(text("DROP INDEX IF EXISTS idx_conv_session_context_embedding;"))

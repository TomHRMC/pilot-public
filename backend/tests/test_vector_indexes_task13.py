"""
Test Suite: Phase 4 Task 13 - Vector Indexes (pgvector Similarity Search)
Tests HNSW index creation for conversation embeddings from Golden Master v2.6h
"""

import numpy as np
import pytest
from sqlalchemy import text

from app.models.ai import ConversationMessage, ConversationSession


class TestVectorIndexExistence:
    """Verify HNSW indexes exist in database"""

    def test_idx_conv_session_context_embedding_exists(self, db_session):
        """Verify idx_conv_session_context_embedding HNSW index exists"""
        result = db_session.execute(
            text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'conversation_session'
              AND indexname = 'idx_conv_session_context_embedding'
        """)
        )
        row = result.fetchone()
        assert row is not None, "idx_conv_session_context_embedding index missing"
        assert "hnsw" in row[1].lower(), "Index is not HNSW type"
        assert "vector_cosine_ops" in row[1], "Index does not use vector_cosine_ops"

    def test_idx_conv_msg_embedding_exists(self, db_session):
        """Verify idx_conv_msg_embedding HNSW index exists"""
        result = db_session.execute(
            text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'conversation_message'
              AND indexname = 'idx_conv_msg_embedding'
        """)
        )
        row = result.fetchone()
        assert row is not None, "idx_conv_msg_embedding index missing"
        assert "hnsw" in row[1].lower(), "Index is not HNSW type"
        assert "vector_cosine_ops" in row[1], "Index does not use vector_cosine_ops"

    def test_both_indexes_have_correct_parameters(self, db_session):
        """Verify both HNSW indexes have correct m and ef_construction parameters"""
        result = db_session.execute(
            text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE indexname IN ('idx_conv_session_context_embedding', 'idx_conv_msg_embedding')
            ORDER BY indexname
        """)
        )
        rows = result.fetchall()
        assert len(rows) == 2, "Expected 2 HNSW indexes"

        for row in rows:
            indexdef = row[1]
            assert "m='16'" in indexdef or "m=16" in indexdef, (
                f"Index {row[0]} missing m=16 parameter"
            )
            assert (
                "ef_construction='64'" in indexdef or "ef_construction=64" in indexdef
            ), f"Index {row[0]} missing ef_construction=64 parameter"


class TestSessionEmbeddingSimilaritySearch:
    """Test conversation_session vector similarity queries"""

    def test_session_similarity_query_executes(
        self, db_session, test_tenant, test_user
    ):
        """Verify similarity queries on conversation_session execute without error"""
        # Create test sessions with embeddings
        for i in range(10):
            embedding = np.random.rand(1024).tolist()
            sess = ConversationSession(
                tenant_id=test_tenant.id,
                user_id=test_user.id,
                context_embedding=embedding,
            )
            db_session.add(sess)
        db_session.commit()

        # Query for similar sessions using <-> operator
        query_embedding = np.random.rand(1024).tolist()
        query_vector = f"[{','.join(map(str, query_embedding))}]"

        # Verify query executes without error
        result = db_session.execute(
            text(f"""
            SELECT id FROM conversation_session
            ORDER BY context_embedding <-> '{query_vector}'::vector
            LIMIT 5
        """)
        )
        rows = result.fetchall()
        assert len(rows) <= 5, "Query returned too many rows"
        assert len(rows) > 0, "Query returned no rows"

    def test_session_similarity_returns_correct_results(
        self, db_session, test_tenant, test_user
    ):
        """Verify similarity search returns sessions in correct order"""
        # Create sessions with known embeddings
        base_embedding = [1.0] * 1024

        # Session 1: Identical to query
        sess1 = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            context_embedding=base_embedding,
        )
        db_session.add(sess1)

        # Session 2: Slightly different
        different_embedding = base_embedding.copy()
        different_embedding[0] = 0.5
        sess2 = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            context_embedding=different_embedding,
        )
        db_session.add(sess2)

        db_session.commit()

        # Query for sessions similar to base_embedding
        query_vector = f"[{','.join(map(str, base_embedding))}]"
        result = db_session.execute(
            text(f"""
            SELECT id FROM conversation_session
            WHERE tenant_id = '{test_tenant.id}'
            ORDER BY context_embedding <-> '{query_vector}'::vector
            LIMIT 2
        """)
        )
        rows = result.fetchall()

        # Sess1 should be first (most similar)
        assert rows[0][0] == sess1.id, "Most similar session not returned first"

    def test_session_similarity_with_null_embeddings(
        self, db_session, test_tenant, test_user
    ):
        """Verify queries handle NULL embeddings gracefully"""
        # Create session with NULL embedding
        sess_null = ConversationSession(
            tenant_id=test_tenant.id, user_id=test_user.id, context_embedding=None
        )
        db_session.add(sess_null)

        # Create session with actual embedding
        embedding = [0.5] * 1024
        sess_with_embedding = ConversationSession(
            tenant_id=test_tenant.id, user_id=test_user.id, context_embedding=embedding
        )
        db_session.add(sess_with_embedding)
        db_session.commit()

        # Query should skip NULL embeddings
        query_vector = f"[{','.join(map(str, embedding))}]"
        result = db_session.execute(
            text(f"""
            SELECT id FROM conversation_session
            WHERE context_embedding IS NOT NULL
            ORDER BY context_embedding <-> '{query_vector}'::vector
            LIMIT 5
        """)
        )
        rows = result.fetchall()

        # Should only return session with non-NULL embedding
        assert len(rows) == 1, (
            "Query should only return sessions with non-NULL embeddings"
        )
        assert rows[0][0] == sess_with_embedding.id


class TestMessageEmbeddingSimilaritySearch:
    """Test conversation_message vector similarity queries"""

    def test_message_similarity_query_executes(
        self, db_session, test_tenant, test_user
    ):
        """Verify similarity queries on conversation_message execute without error"""
        # Create test conversation session
        conv_session = ConversationSession(
            tenant_id=test_tenant.id, user_id=test_user.id
        )
        db_session.add(conv_session)
        db_session.flush()

        # Create test messages with embeddings
        for i in range(10):
            embedding = np.random.rand(1024).tolist()
            msg = ConversationMessage(
                session_id=conv_session.id,
                tenant_id=test_tenant.id,
                content_text=f"Test message {i}",
                role="user",
                embedding=embedding,
            )
            db_session.add(msg)
        db_session.commit()

        # Query for similar messages
        query_embedding = np.random.rand(1024).tolist()
        query_vector = f"[{','.join(map(str, query_embedding))}]"

        # Verify query executes without error
        result = db_session.execute(
            text(f"""
            SELECT id FROM conversation_message
            ORDER BY embedding <-> '{query_vector}'::vector
            LIMIT 5
        """)
        )
        rows = result.fetchall()
        assert len(rows) <= 5, "Query returned too many rows"
        assert len(rows) > 0, "Query returned no rows"

    def test_message_similarity_returns_correct_results(
        self, db_session, test_tenant, test_user
    ):
        """Verify message similarity search returns messages in correct order"""
        # Create conversation session
        conv_session = ConversationSession(
            tenant_id=test_tenant.id, user_id=test_user.id
        )
        db_session.add(conv_session)
        db_session.flush()

        # Create messages with known embeddings
        base_embedding = [0.5] * 1024

        # Message 1: Identical to query
        msg1 = ConversationMessage(
            session_id=conv_session.id,
            tenant_id=test_tenant.id,
            content_text="Test message 1",
            role="user",
            embedding=base_embedding,
        )
        db_session.add(msg1)

        # Message 2: Different
        different_embedding = [0.1] * 1024
        msg2 = ConversationMessage(
            session_id=conv_session.id,
            tenant_id=test_tenant.id,
            content_text="Test message 2",
            role="assistant",
            embedding=different_embedding,
        )
        db_session.add(msg2)

        db_session.commit()

        # Query for messages similar to base_embedding
        query_vector = f"[{','.join(map(str, base_embedding))}]"
        result = db_session.execute(
            text(f"""
            SELECT id FROM conversation_message
            WHERE session_id = '{conv_session.id}'
            ORDER BY embedding <-> '{query_vector}'::vector
            LIMIT 2
        """)
        )
        rows = result.fetchall()

        # Msg1 should be first (most similar)
        assert rows[0][0] == msg1.id, "Most similar message not returned first"

    def test_message_similarity_with_null_embeddings(
        self, db_session, test_tenant, test_user
    ):
        """Verify message queries handle NULL embeddings gracefully"""
        # Create conversation session
        conv_session = ConversationSession(
            tenant_id=test_tenant.id, user_id=test_user.id
        )
        db_session.add(conv_session)
        db_session.flush()

        # Create message with NULL embedding
        msg_null = ConversationMessage(
            session_id=conv_session.id,
            tenant_id=test_tenant.id,
            content_text="No embedding",
            role="user",
            embedding=None,
        )
        db_session.add(msg_null)

        # Create message with actual embedding
        embedding = [0.5] * 1024
        msg_with_embedding = ConversationMessage(
            session_id=conv_session.id,
            tenant_id=test_tenant.id,
            content_text="Has embedding",
            role="user",
            embedding=embedding,
        )
        db_session.add(msg_with_embedding)
        db_session.commit()

        # Query should skip NULL embeddings
        query_vector = f"[{','.join(map(str, embedding))}]"
        result = db_session.execute(
            text(f"""
            SELECT id FROM conversation_message
            WHERE embedding IS NOT NULL
            ORDER BY embedding <-> '{query_vector}'::vector
            LIMIT 5
        """)
        )
        rows = result.fetchall()

        # Should only return message with non-NULL embedding
        assert len(rows) == 1, (
            "Query should only return messages with non-NULL embeddings"
        )
        assert rows[0][0] == msg_with_embedding.id


class TestVectorIndexPerformance:
    """Test vector index performance characteristics"""

    def test_pgvector_extension_installed(self, db_session):
        """Verify pgvector extension is installed"""
        result = db_session.execute(
            text("""
            SELECT * FROM pg_extension WHERE extname = 'vector'
        """)
        )
        row = result.fetchone()
        assert row is not None, "pgvector extension not installed"

    def test_session_context_embedding_column_type(self, db_session):
        """Verify conversation_session.context_embedding is vector type"""
        result = db_session.execute(
            text("""
            SELECT data_type, udt_name
            FROM information_schema.columns
            WHERE table_name = 'conversation_session'
              AND column_name = 'context_embedding'
        """)
        )
        row = result.fetchone()
        assert row is not None, "context_embedding column not found"
        # pgvector uses USER-DEFINED type
        assert row[1] == "vector", "context_embedding is not vector type"

    def test_message_embedding_column_type(self, db_session):
        """Verify conversation_message.embedding is vector type"""
        result = db_session.execute(
            text("""
            SELECT data_type, udt_name
            FROM information_schema.columns
            WHERE table_name = 'conversation_message'
              AND column_name = 'embedding'
        """)
        )
        row = result.fetchone()
        assert row is not None, "embedding column not found"
        assert row[1] == "vector", "embedding is not vector type"

    def test_indexes_are_hnsw_type(self, db_session):
        """Verify indexes use HNSW algorithm (not IVFFlat or other)"""
        result = db_session.execute(
            text("""
            SELECT 
                indexname,
                indexdef
            FROM pg_indexes
            WHERE indexname IN ('idx_conv_session_context_embedding', 'idx_conv_msg_embedding')
            ORDER BY indexname
        """)
        )
        rows = result.fetchall()

        assert len(rows) == 2, "Expected 2 vector indexes"
        for row in rows:
            assert "hnsw" in row[1].lower(), f"Index {row[0]} is not HNSW type"
            assert "ivfflat" not in row[1].lower(), (
                f"Index {row[0]} should not be IVFFlat"
            )

    def test_session_embedding_supports_1024_dimensions(
        self, db_session, test_tenant, test_user
    ):
        """Verify context_embedding accepts 1024-dimension vectors"""
        # Create session with 1024-dimension embedding
        embedding_1024 = np.random.rand(1024).tolist()
        sess = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            context_embedding=embedding_1024,
        )
        db_session.add(sess)
        db_session.commit()

        # Retrieve and verify
        from sqlmodel import select

        stmt = select(ConversationSession).where(ConversationSession.id == sess.id)
        retrieved = db_session.exec(stmt).first()
        assert retrieved is not None
        assert retrieved.context_embedding is not None

    def test_message_embedding_supports_1024_dimensions(
        self, db_session, test_tenant, test_user
    ):
        """Verify message embedding accepts 1024-dimension vectors"""
        # Create conversation session
        conv_session = ConversationSession(
            tenant_id=test_tenant.id, user_id=test_user.id
        )
        db_session.add(conv_session)
        db_session.flush()

        # Create message with 1024-dimension embedding
        embedding_1024 = np.random.rand(1024).tolist()
        msg = ConversationMessage(
            session_id=conv_session.id,
            tenant_id=test_tenant.id,
            content_text="Test message",
            role="user",
            embedding=embedding_1024,
        )
        db_session.add(msg)
        db_session.commit()

        # Retrieve and verify
        from sqlmodel import select

        stmt = select(ConversationMessage).where(ConversationMessage.id == msg.id)
        retrieved = db_session.exec(stmt).first()
        assert retrieved is not None
        assert retrieved.embedding is not None


class TestVectorIndexEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_embedding_vector_rejected(self, db_session, test_tenant, test_user):
        """Verify empty vectors are rejected (must be 1024 dimensions)"""
        with pytest.raises(Exception):  # Will raise database error
            sess = ConversationSession(
                tenant_id=test_tenant.id,
                user_id=test_user.id,
                context_embedding=[],  # Empty vector
            )
            db_session.add(sess)
            db_session.commit()
        db_session.rollback()

    def test_wrong_dimension_embedding_rejected(
        self, db_session, test_tenant, test_user
    ):
        """Verify vectors with wrong dimensions are rejected"""
        with pytest.raises(Exception):  # Will raise database error
            sess = ConversationSession(
                tenant_id=test_tenant.id,
                user_id=test_user.id,
                context_embedding=[0.5] * 512,  # Wrong dimension (512 instead of 1024)
            )
            db_session.add(sess)
            db_session.commit()
        db_session.rollback()

    def test_similarity_search_limit_works(self, db_session, test_tenant, test_user):
        """Verify LIMIT clause works correctly in similarity search"""
        # Create multiple sessions
        for i in range(20):
            embedding = np.random.rand(1024).tolist()
            sess = ConversationSession(
                tenant_id=test_tenant.id,
                user_id=test_user.id,
                context_embedding=embedding,
            )
            db_session.add(sess)
        db_session.commit()

        # Query with LIMIT
        query_embedding = np.random.rand(1024).tolist()
        query_vector = f"[{','.join(map(str, query_embedding))}]"

        for limit in [1, 5, 10]:
            result = db_session.execute(
                text(f"""
                SELECT id FROM conversation_session
                ORDER BY context_embedding <-> '{query_vector}'::vector
                LIMIT {limit}
            """)
            )
            rows = result.fetchall()
            assert len(rows) == limit, f"LIMIT {limit} returned {len(rows)} rows"

    def test_multiple_similarity_queries_same_session(
        self, db_session, test_tenant, test_user
    ):
        """Verify multiple similarity queries can be run in same session"""
        # Create test data
        for i in range(10):
            embedding = np.random.rand(1024).tolist()
            sess = ConversationSession(
                tenant_id=test_tenant.id,
                user_id=test_user.id,
                context_embedding=embedding,
            )
            db_session.add(sess)
        db_session.commit()

        # Run multiple queries
        for _ in range(3):
            query_embedding = np.random.rand(1024).tolist()
            query_vector = f"[{','.join(map(str, query_embedding))}]"

            result = db_session.execute(
                text(f"""
                SELECT id FROM conversation_session
                ORDER BY context_embedding <-> '{query_vector}'::vector
                LIMIT 3
            """)
            )
            rows = result.fetchall()
            assert len(rows) == 3, "Each query should return 3 results"

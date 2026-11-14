# Task 13: Vector Indexes (pgvector Similarity Search)

**Reference:** `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` - Task 13
**Authority:** `dev-docs/db-design/pilot-db-schema-v2.6h.json`
**Type:** Phase 4 - Advanced Indexing
**Priority:** MEDIUM (Voice AI feature enablement)

---

## Context

We're building AevoFab AI, an AI-powered SaaS platform for electrical contractors with voice-controlled quoting and QuickBooks integration. Following the 80/20 rule to reach MVP quickly.

This is a **Phase 4 Advanced Indexing task** to achieve 100% alignment between our SQLModel implementations and the Golden Master Database Schema (v2.6h JSON). This is NOT a new feature - it's surgical corrections to ensure database-level performance optimization for Voice AI semantic similarity search.

---

## Completed So Far

**Phase 1: Foundation (COMPLETE - March 30-31, 2026):**
- ✅ Task 1: Timezone enforcement (9 columns fixed)
- ✅ Task 2: Citext conversion for user email
- ✅ Task 3: QuickBooks identity rules on Customer table

**Phase 2: Functions & Triggers (COMPLETE - March 31, 2026):**
- ✅ Task 4: Missing PL/pgSQL functions (3 functions + 200 triggers)
- ✅ Task 5: Function naming standard compliance
- ✅ Task 6: Audit trigger coverage (85 audit triggers)
- ✅ Task 7: Operational trigger verification (293 total triggers)

**Phase 3: Data Integrity (COMPLETE - April 1, 2026):**
- ✅ Task 8: Missing unique constraints (4/4 complete)
- ✅ Task 9: Missing check constraints (9/9 complete)
- ✅ Task 10: Missing temporal exclusion constraints (6/6 complete)

**Phase 4: Advanced Indexing (PARTIAL - April 1, 2026):**
- ✅ Task 11: Partial indexes (2/2 complete - invoice_balance, job_expense_unbilled)
- ✅ Task 12: Partial unique indexes (2/2 complete - user_email_primary, global_primary_email)
- 📋 Task 13: Vector indexes (not started) ← **CURRENT TASK**

**Current Test Baseline:** 553 tests passing (100%)
**See:** `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` for full context

---

## Current Task: Vector Indexes (pgvector Similarity Search)

**Effort:** 1 day
**Gap Reference:** Analysis Section 4 - Missing Indexes (Vector)

The `conversation_session` and `conversation_message` tables have `embedding` columns (`vector(1024)`) for semantic similarity search, but **no HNSW indexes**. Without them, vector searches are unusably slow (full table scan takes ~5 seconds). This task adds HNSW indexes to enable real-time Voice AI context retrieval (<100ms queries).

### What Needs to Be Fixed

| # | Entity/Component | Issue | Impact | Complexity |
|---|------------------|-------|--------|------------|
| **1** | `conversation_session.embedding` | Missing HNSW index for vector similarity search | Voice AI session similarity queries timeout (5s) | MEDIUM |
| **2** | `conversation_message.embedding` | Missing HNSW index for vector similarity search | Voice AI message context retrieval unusable (5s) | MEDIUM |

---

## ⚠️ BEFORE YOU START - Establish Regression Baseline

**CRITICAL:** You MUST capture the current test baseline BEFORE making ANY changes. This ensures we can detect regressions.

### Step 1: Activate Virtual Environment

All Python and pytest commands MUST be run in the virtual environment:

```bash
cd backend
source .venv/bin/activate
```

### Step 2: Run Regression Tests (Non-Integration)

```bash
# Run all tests EXCEPT integration tests
pytest --ignore=tests/integration/ tests/ -v

# Concise output to capture baseline count
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Record the output:** `553 tests passing` (expected baseline)

Example output:
```
========================== 553 passed in 45.23s ==========================
```

### Step 3: Run ALL Tests (Including Integration)

```bash
# Run ALL tests
pytest tests/ -v

# Concise output
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Record the output:** `[BASELINE_TOTAL_COUNT] tests passing`

Example output:
```
========================== 580 passed in 62.11s ==========================
```

### Step 4: Document Your Baseline

**Write down these numbers before proceeding:**
- Non-Integration Baseline: `553/553` passing
- Total Tests Baseline: `___/___` passing

**These are your regression checkpoints. All these tests MUST still pass after your work.**

---

## Requirements

### 1. Implementation Details

#### Gap 1: conversation_session.embedding - HNSW Index Missing

**Problem:** 
The `conversation_session` table stores 1024-dimension embeddings for semantic similarity search (e.g., "Show me other times Mike asked about service panels"). Without an HNSW index, queries perform a full table scan taking ~5 seconds, making Voice AI context retrieval unusable.

**Current Performance:**
```sql
-- Without index: Sequential scan of ALL vectors
SELECT * FROM conversation_session 
ORDER BY embedding <-> '[0.1, 0.2, ..., 0.1024]'::vector 
LIMIT 10;
-- Query time: ~5 seconds (unusable for real-time Voice AI)
```

**Target Performance:**
```sql
-- With HNSW index: Index scan
-- Query time: ~50ms (100x faster)
```

**Migration SQL:**
```sql
-- Enable pgvector extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create HNSW index with tuning parameters
CREATE INDEX CONCURRENTLY idx_conv_session_embedding 
ON conversation_session 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Index parameters explained:
-- m = 16: Number of connections per node (higher = more accurate, slower build)
-- ef_construction = 64: Search quality during build (higher = better recall, slower build)
-- vector_cosine_ops: Use cosine distance for similarity (dot product normalized)
```

**What This Enables:**
- Find similar conversation sessions (semantic grouping)
- Voice AI context retrieval for multi-session patterns
- "Did this customer ask about X before?" queries

---

#### Gap 2: conversation_message.embedding - HNSW Index Missing

**Problem:**
The `conversation_message` table stores embeddings for individual messages within conversations. Without an HNSW index, context window retrieval for multi-turn conversations is too slow for real-time use.

**Migration SQL:**
```sql
-- Create HNSW index for message embeddings
CREATE INDEX CONCURRENTLY idx_conv_msg_embedding 
ON conversation_message 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**What This Enables:**
- Find similar messages in conversation history
- Context window retrieval for multi-turn conversations (<100ms)
- Semantic deduplication ("Did customer already ask this?")

---

### 2. Database Query Tools

**You have access to the postgres-local MCP server for direct database queries:**

```python
# Example: Verify pgvector extension is installed
await mcp__postgres_local__query({
    "sql": """
        SELECT * FROM pg_extension WHERE extname = 'vector';
    """
})

# Example: Check if embeddings exist in tables
await mcp__postgres_local__query({
    "sql": """
        SELECT 
            COUNT(*) as total_sessions,
            COUNT(embedding) as sessions_with_embeddings
        FROM conversation_session;
    """
})

# Example: Verify index exists and is HNSW type
await mcp__postgres_local__query({
    "sql": """
        SELECT 
            indexname,
            indexdef
        FROM pg_indexes
        WHERE tablename IN ('conversation_session', 'conversation_message')
          AND indexname LIKE '%embedding%';
    """
})
```

Use this tool to:
- Verify pgvector extension is installed
- Check if embeddings exist in tables (may be NULL in test data)
- Verify indexes exist after migration
- Analyze query plans (EXPLAIN ANALYZE)

---

### 3. Implementation Order

Execute in this exact sequence:

1. **✅ Establish Regression Baseline** (see "Before You Start" section above)

2. **Pre-Migration Environment Check**
   - Verify pgvector extension is installed
   - Check if conversation tables exist
   - Verify embedding columns exist and are `vector(1024)` type
   - Document current table row counts

3. **Create Manual Migration** (autogenerate won't work for HNSW)
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision -m "add_vector_indexes_for_embeddings_task13"
   ```

4. **Edit Migration File**
   - Add `CREATE EXTENSION IF NOT EXISTS vector;`
   - Add both HNSW index creation statements with `CONCURRENTLY`
   - Add both index drop statements in downgrade()
   - **CRITICAL:** Use `op.execute()` for all statements (autogenerate can't handle HNSW)

5. **Apply Migration**
   ```bash
   alembic upgrade head
   ```
   
   **Note:** HNSW index creation can take minutes to hours depending on data volume. For test database with minimal data, should be <1 minute.

6. **Create Test Suite**
   - Create `backend/tests/test_vector_indexes_task13.py`
   - Write comprehensive tests (see Test Requirements below)
   - **CRITICAL:** Use `session.query()` NOT `session.exec()` to avoid deprecation warnings

7. **Run New Tests**
   ```bash
   pytest tests/test_vector_indexes_task13.py -v
   ```

8. **Run Regression Tests** (see "After You Complete" section below)

9. **Update Documentation** (see Documentation Update section below)

---

### 4. Test Requirements

**⚠️ ZERO FAILING TESTS POLICY:**
- **ALL 553 existing tests MUST still pass** (baseline cannot regress)
- **ALL new tests MUST pass** (vector index verification)
- **Target: 571/571 passing (100%)** (553 baseline + 18 new tests)

**Test File:** `backend/tests/test_vector_indexes_task13.py`

**Test Standards:**

```python
"""
Test Suite: Phase 4 Task 13 - Vector Indexes (pgvector Similarity Search)
Tests HNSW index creation for conversation embeddings from Golden Master v2.6h
"""
import pytest
import numpy as np
from sqlmodel import Session, select
from sqlalchemy import text

from app.models.voice import ConversationSession, ConversationMessage
from app.models.core import User
from app.models.crm import Tenant

class TestVectorIndexExistence:
    """Verify HNSW indexes exist in database"""
    
    def test_idx_conv_session_embedding_exists(self, session: Session):
        """Verify idx_conv_session_embedding HNSW index exists"""
        result = session.execute(text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'conversation_session'
              AND indexname = 'idx_conv_session_embedding'
        """))
        row = result.fetchone()
        assert row is not None, "idx_conv_session_embedding index missing"
        assert "hnsw" in row[1].lower(), "Index is not HNSW type"
        assert "vector_cosine_ops" in row[1], "Index does not use vector_cosine_ops"
    
    def test_idx_conv_msg_embedding_exists(self, session: Session):
        """Verify idx_conv_msg_embedding HNSW index exists"""
        result = session.execute(text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'conversation_message'
              AND indexname = 'idx_conv_msg_embedding'
        """))
        row = result.fetchone()
        assert row is not None, "idx_conv_msg_embedding index missing"
        assert "hnsw" in row[1].lower(), "Index is not HNSW type"
        assert "vector_cosine_ops" in row[1], "Index does not use vector_cosine_ops"

class TestSessionEmbeddingSimilaritySearch:
    """Test conversation_session vector similarity queries"""
    
    def test_session_similarity_query_uses_index(self, session: Session, test_tenant):
        """Verify similarity queries on conversation_session use HNSW index"""
        # Create test sessions with embeddings
        sessions = []
        for i in range(10):
            embedding = np.random.rand(1024).tolist()
            sess = ConversationSession(
                tenant_id=test_tenant.id,
                embedding=embedding
            )
            sessions.append(sess)
            session.add(sess)
        session.commit()
        
        # Query for similar sessions using <-> operator
        query_embedding = np.random.rand(1024).tolist()
        query_vector = f"[{','.join(map(str, query_embedding))}]"
        
        # Check query plan uses index
        explain_result = session.execute(text(f"""
            EXPLAIN (FORMAT TEXT)
            SELECT id FROM conversation_session
            ORDER BY embedding <-> '{query_vector}'::vector
            LIMIT 5
        """))
        plan = '\n'.join([row[0] for row in explain_result])
        
        # Index should be ready for use (may show Seq Scan if table too small)
        # Just verify query executes without error
        result = session.execute(text(f"""
            SELECT id FROM conversation_session
            ORDER BY embedding <-> '{query_vector}'::vector
            LIMIT 5
        """))
        rows = result.fetchall()
        assert len(rows) <= 5, "Query returned too many rows"
    
    def test_session_similarity_returns_correct_results(self, session: Session, test_tenant):
        """Verify similarity search returns sessions in correct order"""
        # Create sessions with known embeddings
        base_embedding = [1.0] * 1024
        
        # Session 1: Identical to query
        sess1 = ConversationSession(
            tenant_id=test_tenant.id,
            embedding=base_embedding
        )
        session.add(sess1)
        
        # Session 2: Slightly different
        different_embedding = base_embedding.copy()
        different_embedding[0] = 0.5
        sess2 = ConversationSession(
            tenant_id=test_tenant.id,
            embedding=different_embedding
        )
        session.add(sess2)
        
        session.commit()
        
        # Query for sessions similar to base_embedding
        query_vector = f"[{','.join(map(str, base_embedding))}]"
        result = session.execute(text(f"""
            SELECT id FROM conversation_session
            WHERE tenant_id = {test_tenant.id}
            ORDER BY embedding <-> '{query_vector}'::vector
            LIMIT 2
        """))
        rows = result.fetchall()
        
        # Sess1 should be first (most similar)
        assert rows[0][0] == sess1.id, "Most similar session not returned first"

class TestMessageEmbeddingSimilaritySearch:
    """Test conversation_message vector similarity queries"""
    
    def test_message_similarity_query_uses_index(self, session: Session, test_tenant):
        """Verify similarity queries on conversation_message use HNSW index"""
        # Create test conversation session
        conv_session = ConversationSession(tenant_id=test_tenant.id)
        session.add(conv_session)
        session.flush()
        
        # Create test messages with embeddings
        messages = []
        for i in range(10):
            embedding = np.random.rand(1024).tolist()
            msg = ConversationMessage(
                conversation_session_id=conv_session.id,
                content=f"Test message {i}",
                role="user",
                embedding=embedding
            )
            messages.append(msg)
            session.add(msg)
        session.commit()
        
        # Query for similar messages
        query_embedding = np.random.rand(1024).tolist()
        query_vector = f"[{','.join(map(str, query_embedding))}]"
        
        # Verify query executes without error
        result = session.execute(text(f"""
            SELECT id FROM conversation_message
            ORDER BY embedding <-> '{query_vector}'::vector
            LIMIT 5
        """))
        rows = result.fetchall()
        assert len(rows) <= 5, "Query returned too many rows"
    
    def test_message_similarity_returns_correct_results(self, session: Session, test_tenant):
        """Verify message similarity search returns messages in correct order"""
        # Create conversation session
        conv_session = ConversationSession(tenant_id=test_tenant.id)
        session.add(conv_session)
        session.flush()
        
        # Create messages with known embeddings
        base_embedding = [0.5] * 1024
        
        # Message 1: Identical to query
        msg1 = ConversationMessage(
            conversation_session_id=conv_session.id,
            content="Test message 1",
            role="user",
            embedding=base_embedding
        )
        session.add(msg1)
        
        # Message 2: Different
        different_embedding = [0.1] * 1024
        msg2 = ConversationMessage(
            conversation_session_id=conv_session.id,
            content="Test message 2",
            role="assistant",
            embedding=different_embedding
        )
        session.add(msg2)
        
        session.commit()
        
        # Query for messages similar to base_embedding
        query_vector = f"[{','.join(map(str, base_embedding))}]"
        result = session.execute(text(f"""
            SELECT id FROM conversation_message
            WHERE conversation_session_id = {conv_session.id}
            ORDER BY embedding <-> '{query_vector}'::vector
            LIMIT 2
        """))
        rows = result.fetchall()
        
        # Msg1 should be first (most similar)
        assert rows[0][0] == msg1.id, "Most similar message not returned first"

class TestVectorIndexPerformance:
    """Test vector index performance characteristics"""
    
    def test_pgvector_extension_installed(self, session: Session):
        """Verify pgvector extension is installed"""
        result = session.execute(text("""
            SELECT * FROM pg_extension WHERE extname = 'vector'
        """))
        row = result.fetchone()
        assert row is not None, "pgvector extension not installed"
    
    def test_session_embedding_column_type(self, session: Session):
        """Verify conversation_session.embedding is vector(1024) type"""
        result = session.execute(text("""
            SELECT data_type, udt_name
            FROM information_schema.columns
            WHERE table_name = 'conversation_session'
              AND column_name = 'embedding'
        """))
        row = result.fetchone()
        assert row is not None, "embedding column not found"
        # pgvector uses USER-DEFINED type
        assert row[1] == "vector", "embedding is not vector type"
    
    def test_message_embedding_column_type(self, session: Session):
        """Verify conversation_message.embedding is vector(1024) type"""
        result = session.execute(text("""
            SELECT data_type, udt_name
            FROM information_schema.columns
            WHERE table_name = 'conversation_message'
              AND column_name = 'embedding'
        """))
        row = result.fetchone()
        assert row is not None, "embedding column not found"
        assert row[1] == "vector", "embedding is not vector type"
```

**Required Test Coverage (Minimum 18 Tests):**
- [x] Index existence verification (2 tests)
- [x] Session similarity query uses index (1 test)
- [x] Session similarity returns correct results (1 test)
- [x] Message similarity query uses index (1 test)
- [x] Message similarity returns correct results (1 test)
- [x] pgvector extension installed (1 test)
- [x] Embedding column types correct (2 tests)
- [ ] Additional edge case tests as needed

**Test Fixtures:**
Review `backend/tests/conftest.py` for available fixtures:
- `session` - Database session with auto-rollback
- `test_tenant` - Test tenant record
- `test_user` - Test user record

**Note:** You may need to add numpy to test dependencies for generating random embeddings.

---

### 5. Database Verification

**After Migration Applied:**

Use the MCP server or psql to verify indexes:

```sql
-- Verify pgvector extension exists
SELECT * FROM pg_extension WHERE extname = 'vector';
-- Expected: 1 row (extension installed)

-- Verify HNSW indexes exist
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE indexname IN (
    'idx_conv_session_embedding',
    'idx_conv_msg_embedding'
)
ORDER BY indexname;

-- Expected output:
-- public | conversation_session | idx_conv_session_embedding | CREATE INDEX idx_conv_session_embedding ON conversation_session USING hnsw (embedding vector_cosine_ops) WITH (m='16', ef_construction='64')
-- public | conversation_message | idx_conv_msg_embedding | CREATE INDEX idx_conv_msg_embedding ON conversation_message USING hnsw (embedding vector_cosine_ops) WITH (m='16', ef_construction='64')

-- Verify index sizes
SELECT 
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE indexname LIKE '%embedding%'
ORDER BY indexname;

-- Check index usage stats (after running similarity queries)
SELECT 
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE indexname LIKE '%embedding%'
ORDER BY indexname;
```

---

## 🎯 AFTER YOU COMPLETE - Verify No Regressions

**CRITICAL:** After all implementation and new tests pass, you MUST verify the regression baseline.

### Step 1: Activate Virtual Environment

```bash
cd backend
source .venv/bin/activate
```

### Step 2: Run Non-Integration Tests

```bash
# Run all tests EXCEPT integration tests
pytest --ignore=tests/integration/ tests/ -v

# Concise output
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Expected:** `571 passed` (553 baseline + 18 new tests)

### Step 3: Run ALL Tests (Including Integration)

```bash
# Run ALL tests
pytest tests/ -v

# Concise output
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Expected:** `[BASELINE_TOTAL_COUNT + 18] passed`

### Step 4: Verify 100% Pass Rate

**If ANY tests fail:**
1. Identify which tests are failing
2. Determine if they are:
   - New tests you wrote (fix them)
   - Existing tests that regressed (CRITICAL - fix immediately)
3. Fix ALL failing tests before proceeding
4. Re-run regression tests until 100% pass rate

**Regression Analysis:**
- New tests failing → Fix your test code
- Existing tests failing → Your changes broke something - ROLLBACK and fix
- Cannot achieve 100% → Create fix document (see Zero Tolerance Policy below)

---

## Documentation Update

### Update Project Plan Document

**File to Update:** `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md`

Find Task 13 section and update with:

```markdown
### Task 13: Vector Indexes (pgvector Similarity Search)

**Status:** ✅ COMPLETE (2026-04-01)
**Effort:** 1 day (actual)
**Priority:** MEDIUM
**Gap Reference:** Analysis Section 4 - Missing Indexes (Vector)

**Completed 2 HNSW vector indexes:**
- ✅ `idx_conv_session_embedding` - Session similarity search optimization
- ✅ `idx_conv_msg_embedding` - Message similarity search optimization

**Implementation Summary:**

#### 1. idx_conv_session_embedding - Session Similarity Index
- **Index:** `CREATE INDEX idx_conv_session_embedding ON conversation_session USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64)`
- **Purpose:** Enable real-time Voice AI session similarity search
- **Performance:** Sequential scan (5s) → HNSW index scan (<100ms) - 50x faster
- **Test:** `test_session_similarity_query_uses_index`, `test_session_similarity_returns_correct_results` ✅ PASSING

#### 2. idx_conv_msg_embedding - Message Similarity Index
- **Index:** `CREATE INDEX idx_conv_msg_embedding ON conversation_message USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64)`
- **Purpose:** Enable context window retrieval for multi-turn conversations
- **Performance:** Sequential scan (5s) → HNSW index scan (<100ms) - 50x faster
- **Test:** `test_message_similarity_query_uses_index`, `test_message_similarity_returns_correct_results` ✅ PASSING

**Migration:** `2026_04_01_HHMM-[hash]_add_vector_indexes_for_embeddings_task13.py`
**Test Suite:** `test_vector_indexes_task13.py` - 18 tests
**Final Test Results:** 571/571 tests passing (100%)

**Database Verification:**
- pgvector extension enabled ✅
- Both HNSW indexes confirmed active ✅
- Index definitions match Golden Master specification ✅
- Migration upgrade/downgrade tested successfully ✅

**Test Coverage Breakdown:**
- New tests added: 18
- Baseline maintained: 553
- Total passing: 571/571 (100%)
- Test categories: Index existence (2), Session similarity (2), Message similarity (2), Performance/Schema (3), Additional edge cases (9)

**Key Implementation Notes:**
- Used manual migration (SQLModel/autogenerate doesn't support HNSW)
- `CREATE INDEX CONCURRENTLY` for production-safe deployment
- HNSW tuning: m=16 (connections), ef_construction=64 (build quality)
- vector_cosine_ops operator for normalized dot product similarity
- Test embeddings generated with numpy random vectors
- Index creation time <1 minute on test database
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

- [ ] **Regression baseline captured** (non-integration: 553, total: ___ tests)
- [ ] **pgvector extension verified installed** (or installed by migration)
- [ ] **Manual migration created** (autogenerate can't handle HNSW)
- [ ] **Migration includes both HNSW indexes** with correct parameters (m=16, ef_construction=64)
- [ ] **Migration includes downgrade path** (DROP INDEX statements)
- [ ] **Migration uses CONCURRENTLY** for production-safe index creation
- [ ] **Migration applied successfully** (`alembic upgrade head` completes without errors)
- [ ] **All 18 new tests written and passing**
- [ ] **Use session.query() in all tests** (not session.exec() - avoids deprecation warnings)
- [ ] **ALL existing tests still passing** - Zero regression
- [ ] **Non-integration tests:** 571/571 passing (553 + 18)
- [ ] **Total tests:** [BASELINE + 18]/[BASELINE + 18] passing
- [ ] **100% test pass rate** - No failing tests
- [ ] **Database verification query** confirms both indexes active and HNSW type
- [ ] **Migration rollback tested** (`alembic downgrade -1` then `upgrade head` works)
- [ ] **Project plan document updated** with implementation summary

**Zero Tolerance Policy:**
- **Any failing test = INCOMPLETE**
- **Test pass rate MUST be 100%**
- **Regression baseline MUST be maintained or exceeded**
- If tests fail after 10+ attempts, create detailed fix document but mark task incomplete

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` - **Task 13 Details** ⭐
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **GOLDEN MASTER**
- `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Database operations

### Backend Code (Files to Review - NOT Modify)
- `backend/app/models/voice.py` - ConversationSession, ConversationMessage models

### Migration (To Create)
- `backend/migrations/versions/2026_04_01_HHMM-*_add_vector_indexes_for_embeddings_task13.py`

### Tests (To Create)
- `backend/tests/test_vector_indexes_task13.py` - 18 tests minimum

---

## Risk Assessment

**Data Validation Risk:** LOW
- Vector indexes don't affect data integrity
- Tables may have NULL embeddings (index will skip those rows)
- **Mitigation:** Verify embedding columns exist before creating indexes

**Performance Impact:** HIGH (POSITIVE)
- HNSW index creation can take minutes to hours on large datasets
- Test database with minimal data should be <1 minute
- Production deployment: use CONCURRENTLY to avoid table locks
- **Measurement:** Compare query times before/after (EXPLAIN ANALYZE)

**Rollback Complexity:** LOW
- Simple DROP INDEX statements in downgrade()
- No data migration required
- **Testing:** Verify downgrade removes indexes cleanly

**Build Time Risk:** MEDIUM
- HNSW indexes can take significant time to build on large datasets
- Test database should be fast (<1 min)
- **Mitigation:** Use CONCURRENTLY, monitor index creation progress

---

## Notes

- **Virtual Environment Required:** All Python/pytest commands use `source .venv/bin/activate`
- **MCP Server Available:** Use `postgres-local` MCP server for direct database queries
- **Manual Migration Required:** SQLModel/autogenerate can't detect HNSW indexes - must write migration manually
- **CONCURRENTLY Required:** Use `CREATE INDEX CONCURRENTLY` to avoid table locks during index creation
- **Deprecation Warnings:** Use `session.query()` not `session.exec()` in all tests
- **Regression Testing:** Capture baseline BEFORE, verify AFTER - both non-integration and total
- **Golden Master Authority:** The JSON schema is the single source of truth
- **Zero Regression Policy:** All existing tests MUST still pass after changes
- **Cost Impact:** Minimal - indexes improve performance without infrastructure changes
- **Production Safe:** CONCURRENTLY ensures zero downtime during deployment

**Important Patterns:**
- HNSW is an approximate nearest neighbor algorithm (trades perfect accuracy for speed)
- m=16 and ef_construction=64 are recommended starting points
- vector_cosine_ops uses cosine distance (dot product of normalized vectors)
- Recall accuracy should be >90% for production use

**If you get stuck:**
- Check pgvector documentation: https://github.com/pgvector/pgvector
- Verify extension is installed: `SELECT * FROM pg_extension WHERE extname = 'vector';`
- Use MCP server to query index definitions
- Review Task 11 & 12 for partial index patterns
- Verify virtual environment is activated for all commands

---

## Example Task Flow

```bash
# ============================================
# PHASE 1: ESTABLISH BASELINE
# ============================================

# 1. Activate virtual environment
cd backend
source .venv/bin/activate

# 2. Capture non-integration baseline
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: 553 passed

# 3. Capture total baseline
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Record: ___ passed

# ============================================
# PHASE 2: VALIDATE ENVIRONMENT
# ============================================

# 4. Check if pgvector extension is installed (use MCP server or psql)
# If not installed, migration will handle it

# 5. Verify embedding columns exist
# Use MCP server to query information_schema.columns

# ============================================
# PHASE 3: IMPLEMENT CHANGES
# ============================================

# 6. Create manual migration
alembic revision -m "add_vector_indexes_for_embeddings_task13"

# 7. Edit migration file
# Add CREATE EXTENSION IF NOT EXISTS vector;
# Add both HNSW index creation statements
# Add downgrade DROP INDEX statements

# 8. Apply migration
alembic upgrade head

# ============================================
# PHASE 4: VERIFY DATABASE
# ============================================

# 9. Verify indexes in database (using MCP server)
# Query pg_indexes to confirm HNSW indexes exist

# ============================================
# PHASE 5: TEST
# ============================================

# 10. Create test file
# Create backend/tests/test_vector_indexes_task13.py
# REMEMBER: Use session.query() not session.exec()

# 11. Run new tests only
pytest tests/test_vector_indexes_task13.py -v
# Expected: 18 passed

# ============================================
# PHASE 6: REGRESSION VERIFICATION
# ============================================

# 12. Run non-integration regression tests
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 571 passed (553 + 18)

# 13. Run ALL tests (full regression)
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: [BASELINE + 18] passed

# 14. Verify 100% pass rate
# If any failures → FIX IMMEDIATELY

# ============================================
# PHASE 7: ROLLBACK TEST
# ============================================

# 15. Test migration reversibility
alembic downgrade -1
alembic upgrade head
pytest tests/test_vector_indexes_task13.py -v
# Expected: Still 18 passed

# ============================================
# PHASE 8: DOCUMENTATION
# ============================================

# 16. Update project plan document
# Edit phase-4.5-db-schema-sync-to-design-plan.md
# Add completion details, test counts, implementation notes
```

---

## Questions to Ask

**Before starting:**
1. Have I reviewed the Golden Master JSON for vector index specifications?
2. Have I captured the regression baseline (553 non-integration tests)?
3. Have I activated the virtual environment?
4. Do I understand HNSW index parameters (m, ef_construction)?

**During implementation:**
1. Am I creating a MANUAL migration (not using autogenerate)?
2. Am I using `CREATE INDEX CONCURRENTLY` for production safety?
3. Are both indexes using vector_cosine_ops operator?
4. Am I using `session.query()` instead of `session.exec()` in tests?
5. Are my test embeddings the correct dimension (1024)?

**After implementation:**
1. Did I run BOTH non-integration and total regression tests?
2. Do I have 100% test pass rate (no failures)?
3. Did I verify both HNSW indexes exist in database?
4. Have I updated the project plan document?
5. Can the migration be rolled back cleanly?

---

**Ready to Begin!** 🚀

1. ✅ Capture regression baseline (553 non-integration tests)
2. 🔍 Verify pgvector extension and embedding columns
3. 🛠️ Create manual migration with HNSW indexes
4. 📝 Apply migration with CONCURRENTLY
5. ✅ Create comprehensive tests (use session.query(), numpy for embeddings)
6. 🔄 Run regression tests (expect 571 total)
7. 📚 Update project plan document

Remember: Virtual environment required, manual migration (no autogenerate), use CONCURRENTLY, maintain 100% pass rate, test with numpy random vectors!

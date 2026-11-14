"""
Shared database session utility for all seed scripts.

Usage:
    from migrations.scripts._db_utils import get_db_session

    with get_db_session() as db:
        db.execute(text("SELECT 1"))
        db.commit()

    # Or with an explicit URL (E2E / CI override):
    with get_db_session(db_url="postgresql://...") as db:
        ...

E2E Note:
    When DATABASE_URL is set in the environment (e.g. for E2E seeding), this
    utility creates a FRESH engine from that URL rather than using the
    module-level core.db.engine singleton. This is necessary because
    pydantic-settings may have loaded the .env file before the env var was
    set, causing the singleton to point at the wrong database.
"""

import os
import sys
from contextlib import contextmanager
from pathlib import Path

# Ensure the backend directory is on the path so imports resolve correctly.
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from sqlmodel import Session, create_engine  # noqa: E402


@contextmanager
def get_db_session(db_url: str | None = None):
    """
    Context-manager that yields a SQLModel Session.

    Priority for connection URL:
      1. Explicit db_url argument
      2. DATABASE_URL environment variable (read at call time)
      3. core.db.engine singleton (dev DB default)

    Args:
        db_url: Optional explicit database URL. If provided, a fresh engine is
                created for this call only. Use this for E2E/CI isolation.

    Example:
        with get_db_session() as db:
            db.exec(select(MyModel))
            db.commit()

        # E2E override:
        with get_db_session(db_url="postgresql://pilot:pw@localhost:5433/e2e_db") as db:
            db.exec(select(MyModel))
            db.commit()
    """
    url = db_url or os.environ.get("DATABASE_URL")

    if url:
        # Create a fresh engine from the explicit/env URL — avoids stale singletons
        engine = create_engine(url, echo=False)
        with Session(engine) as db:
            yield db
        engine.dispose()
    else:
        # Fall back to the module-level singleton (dev DB default)
        from core.db import engine as _engine

        with Session(_engine) as db:
            yield db

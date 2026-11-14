"""rename_user_endpoint_guard_function

Revision ID: 0a26d3a349c2
Revises: 6b525454c89c
Create Date: 2026-03-31 19:54:56.409370+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0a26d3a349c2"
down_revision: str | None = "6b525454c89c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Rename guard_user_endpoint_primary_email() to guard_user_endpoint_primary_email_fn()
    to comply with Golden Master v2.6h naming standard (all trigger functions must end with _fn).

    Steps:
    1. Rename the function (atomic operation)
    2. Drop existing triggers (they reference the old function name)
    3. Recreate triggers with new function name
    """
    # Step 1: Rename the function
    op.execute("""
        ALTER FUNCTION guard_user_endpoint_primary_email()
        RENAME TO guard_user_endpoint_primary_email_fn;
    """)

    # Step 2: Drop existing triggers (they still reference old function name)
    op.execute("""
        DROP TRIGGER IF EXISTS trg_user_endpoint_guard_biu ON user_endpoint;
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS trg_user_endpoint_guard_bd ON user_endpoint;
    """)

    # Step 3: Recreate triggers with new function name
    op.execute("""
        CREATE TRIGGER trg_user_endpoint_guard_biu
        BEFORE INSERT OR UPDATE ON user_endpoint
        FOR EACH ROW EXECUTE FUNCTION guard_user_endpoint_primary_email_fn();
    """)

    op.execute("""
        CREATE TRIGGER trg_user_endpoint_guard_bd
        BEFORE DELETE ON user_endpoint
        FOR EACH ROW EXECUTE FUNCTION guard_user_endpoint_primary_email_fn();
    """)


def downgrade() -> None:
    """
    Revert function name back to guard_user_endpoint_primary_email().

    Steps:
    1. Drop triggers (they reference new function name)
    2. Rename function back to original name
    3. Recreate triggers with original function name
    """
    # Step 1: Drop existing triggers (they reference new function name)
    op.execute("""
        DROP TRIGGER IF EXISTS trg_user_endpoint_guard_biu ON user_endpoint;
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS trg_user_endpoint_guard_bd ON user_endpoint;
    """)

    # Step 2: Rename function back to original name
    op.execute("""
        ALTER FUNCTION guard_user_endpoint_primary_email_fn()
        RENAME TO guard_user_endpoint_primary_email;
    """)

    # Step 3: Recreate triggers with original function name
    op.execute("""
        CREATE TRIGGER trg_user_endpoint_guard_biu
        BEFORE INSERT OR UPDATE ON user_endpoint
        FOR EACH ROW EXECUTE FUNCTION guard_user_endpoint_primary_email();
    """)

    op.execute("""
        CREATE TRIGGER trg_user_endpoint_guard_bd
        BEFORE DELETE ON user_endpoint
        FOR EACH ROW EXECUTE FUNCTION guard_user_endpoint_primary_email();
    """)

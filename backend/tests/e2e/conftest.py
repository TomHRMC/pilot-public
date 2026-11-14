"""
E2E test conftest — auto-discovered by pytest.

Re-exports all E2E fixtures from conftest_e2e.py so pytest can discover them.
This file must be named conftest.py (not conftest_e2e.py) to be auto-discovered.

SD-10 / E2E-B1 fix: conftest_e2e.py was not discoverable; this shim resolves it.
"""

# Re-export all fixtures from conftest_e2e so they are visible in this package
from tests.e2e.conftest_e2e import (  # noqa: F401
    E2E_DATABASE_URL,
    e2e_client,
    e2e_engine,
    e2e_mock_ai,
    e2e_mock_cognito,
    e2e_mock_entitlement,
    make_owner_auth_header,
    make_tech_auth_header,
)

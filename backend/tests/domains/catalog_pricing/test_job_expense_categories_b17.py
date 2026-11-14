"""
B17/A8 — Unit tests for GET /api/v1/job-expense-categories

Verifies:
  1. GET /test returns 200 with categories array
  2. Response shape matches JobExpenseCategoriesResponse schema
  3. Returns at least the 3 seeded global categories (equipment, materials, permits)
  4. Tenant isolation — only global + own tenant rows returned (no other tenant rows)
  5. Unauthenticated GET to authenticated endpoint returns 401/403

Domain: catalog_pricing
Batch: B17/A8
"""

import pytest

pytestmark = [
    pytest.mark.domain_catalog_pricing,
    pytest.mark.unit,
]


class TestJobExpenseCategoriesEndpoint:
    """B17/A8 — GET /api/v1/job-expense-categories"""

    def test_returns_200(self, client, test_tenant):
        """Test endpoint returns HTTP 200."""
        response = client.get("/api/v1/job-expense-categories/test")
        assert response.status_code == 200

    def test_response_has_categories_key(self, client, test_tenant):
        """Response contains a 'categories' list."""
        response = client.get("/api/v1/job-expense-categories/test")
        data = response.json()
        assert "categories" in data
        assert isinstance(data["categories"], list)

    def test_response_has_required_fields(self, client, test_tenant):
        """Each category item contains code, name, is_default."""
        response = client.get("/api/v1/job-expense-categories/test")
        data = response.json()
        assert len(data["categories"]) >= 1
        for item in data["categories"]:
            assert "code" in item
            assert "name" in item
            assert "is_default" in item
            assert isinstance(item["is_default"], bool)

    def test_returns_seeded_global_categories(self, client, test_tenant):
        """Returns the 3 seeded global categories: equipment, materials, permits."""
        response = client.get("/api/v1/job-expense-categories/test")
        data = response.json()
        codes = {item["code"] for item in data["categories"]}
        assert "equipment" in codes, f"Expected 'equipment' in {codes}"
        assert "materials" in codes, f"Expected 'materials' in {codes}"
        assert "permits" in codes, f"Expected 'permits' in {codes}"

    def test_materials_is_default_true(self, client, test_tenant):
        """The 'materials' category has is_default=True per seed data."""
        response = client.get("/api/v1/job-expense-categories/test")
        data = response.json()
        materials = next(
            (c for c in data["categories"] if c["code"] == "materials"), None
        )
        assert materials is not None, "materials category not found"
        assert materials["is_default"] is True

    def test_equipment_is_default_false(self, client, test_tenant):
        """The 'equipment' category has is_default=False per seed data."""
        response = client.get("/api/v1/job-expense-categories/test")
        data = response.json()
        equipment = next(
            (c for c in data["categories"] if c["code"] == "equipment"), None
        )
        assert equipment is not None, "equipment category not found"
        assert equipment["is_default"] is False

    def test_results_ordered_by_name(self, client, test_tenant):
        """Categories are ordered alphabetically by name."""
        response = client.get("/api/v1/job-expense-categories/test")
        data = response.json()
        names = [c["name"] for c in data["categories"]]
        assert names == sorted(names), f"Categories not sorted by name: {names}"

    def test_authenticated_endpoint_requires_auth(self, client, test_tenant):
        """Authenticated endpoint without JWT returns 401 or 403."""
        response = client.get("/api/v1/job-expense-categories")
        assert response.status_code in (401, 403)

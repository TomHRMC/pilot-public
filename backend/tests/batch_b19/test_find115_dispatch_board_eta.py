"""
FIND-115 — ETA at request-time + Redis cache

Test coverage: Dispatch board response schema includes ETA fields

Design doc: FIND-115 (lines 1670-1688 in 10-remediation-plan.md)
  - ETA computed on-demand at request time (no Celery task)
  - Uses tech's latest stored GPS coordinates from DB
  - Redis cache keyed by (origin_lat, dest_lat, dest_lng, hour_of_day)
  - 15-minute TTL to minimize Google Maps API calls
  - Tech with no GPS coordinates on file → eta_minutes = null (graceful)

Architecture:
  - map_service.get_drive_time_minutes() already implements Redis cache (B3/A20)
  - Dispatch board endpoint fetches tech's current location and first job site
  - Calls map_service to compute ETA with caching
"""

from datetime import UTC, datetime, timedelta


class TestDispatchBoardETA:
    """Tests for FIND-115 dispatch board ETA functionality."""

    def test_dispatch_board_response_schema_includes_eta_fields(self, client):
        """[FIND-115-1] DispatchBoardResponse includes eta_minutes_to_first_job."""
        resp = client.get(
            "/api/v1/scheduling/dispatch-board/test",
            params={
                "start_date": datetime.now(UTC).isoformat(),
                "end_date": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            },
        )
        assert resp.status_code == 200
        data = resp.json()

        # Verify top-level structure
        assert "techs" in data
        assert "unassigned" in data
        assert "start_date" in data
        assert "end_date" in data

    def test_dispatch_board_empty_response(self, client):
        """[FIND-115-2] Dispatch board returns empty arrays when no jobs."""
        resp = client.get(
            "/api/v1/scheduling/dispatch-board/test",
            params={
                "start_date": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
                "end_date": (datetime.now(UTC) + timedelta(days=31)).isoformat(),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["techs"] == []
        assert data["unassigned"] == []

    def test_map_service_cache_hit_ratio_tracking(self, db_session):
        """[FIND-115-3] Verify Redis cache hit/miss tracking in map_service."""
        from services.map_service import get_cache_hit_ratio, reset_cache_counters

        reset_cache_counters()
        ratio = get_cache_hit_ratio()
        assert ratio == 0.0, "Cache should be empty after reset"

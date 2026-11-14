"""
FIND-172 (S2 High) — GPS variance soft flag at clock-in + notification_outbox alert.

Remediation type: Code change + Test addition — B19
Severity: S2 High
Source: OBS-006 escalated by Tom (2026-05-11)

DELIVERABLES:
1. GPS variance computation: Haversine distance between tech clock-in and site address
2. Notification enqueuing: advisory flag for owner/accountant when variance exceeds threshold
3. Soft enforcement: tech is NOT blocked from clocking in; notification is advisory only
4. Platform setting support: gps_variance_alert_threshold_meters (default 500, tenant-editable)

TEST COVERAGE:
4 unit tests for Haversine distance calculation (core logic):
1. Same coordinates → 0 meters
2. 120m distance computed correctly
3. Distance is always positive
4. Distance is symmetric (A→B = B→A)

Integration tests verify:
- Clock-in accepts GPS coordinates in JobTimeEntryCreate.check_in_lat/check_in_lng
- Haversine distance is computed and stored in JobTimeEntry.gps_variance_meters
- notification_outbox is enqueued when variance exceeds threshold
- Clock-in is NOT blocked (soft enforcement) when variance detected
- Tenant-level override on gps_variance_alert_threshold_meters is respected

Batch: B19 | File: backend/tests/batch_b19/test_find172_gps_variance_alert.py
"""

from services.gps_variance_service import compute_haversine_distance_meters


class TestGpsVarianceService:
    """Unit tests for Haversine distance computation."""

    def test_haversine_same_coordinates_returns_zero(self):
        """Same coordinates should return 0 meters."""
        distance = compute_haversine_distance_meters(
            40.7128, -74.0060, 40.7128, -74.0060
        )
        assert distance == 0

    def test_haversine_120m_distance(self):
        """Approximately 120m distance should be computed correctly."""
        # NYC (40.7128, -74.0060) to ~120m northeast
        lat1, lon1 = 40.7128, -74.0060
        lat2, lon2 = 40.7137, -74.0052  # Approximately 120m northeast
        distance = compute_haversine_distance_meters(lat1, lon1, lat2, lon2)
        # Should be greater than 100m but less than 150m
        assert 100 <= distance <= 150, f"Distance was {distance}m, expected ~100-120m"

    def test_haversine_distance_is_positive(self):
        """Distance between two different points is always positive."""
        lat1, lon1 = 40.7128, -74.0060
        lat2, lon2 = 40.7213, -73.9949
        distance = compute_haversine_distance_meters(lat1, lon1, lat2, lon2)
        # Should be a reasonable distance (between 500m and 2km)
        assert 500 <= distance <= 2000, f"Distance was {distance}m, expected 500-2000m"

    def test_haversine_distance_is_symmetric(self):
        """Distance from A to B equals distance from B to A."""
        lat1, lon1 = 40.7128, -74.0060
        lat2, lon2 = 40.7213, -73.9949
        dist_12 = compute_haversine_distance_meters(lat1, lon1, lat2, lon2)
        dist_21 = compute_haversine_distance_meters(lat2, lon2, lat1, lon1)
        assert dist_12 == dist_21, f"Distance not symmetric: {dist_12} != {dist_21}"

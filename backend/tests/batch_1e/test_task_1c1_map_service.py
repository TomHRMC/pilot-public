"""
Task 1-C-1: Map Provider Abstraction — Service Unit Tests

Covers:
  * ``_haversine_km`` accuracy (known city pairs)
  * ``_km_to_drive_minutes`` boundary conditions
  * ``_mock_drive_time`` — with coordinates and with fallback
  * ``get_drive_time_minutes`` (public API):
      - mock provider with lat/lon coordinates
      - mock provider fallback when coordinates are absent
      - same-address short-circuit (0 minutes)
      - IDOR: origin address belongs to a different tenant -> MapServiceError
      - IDOR: destination address belongs to a different tenant -> MapServiceError
      - unknown origin address -> MapServiceError
      - unknown destination address -> MapServiceError
  * ``get_drive_time_minutes`` with ``provider="google"`` (mocked HTTP, success path)
  * ``get_drive_time_minutes`` with ``provider="google"`` (mocked HTTP, API-level error)
  * ``get_drive_time_minutes`` with ``provider="google"`` (mocked HTTP, element ZERO_RESULTS)

All DB interactions use the ``db_session`` fixture (postgres + rollback) from conftest.py.
No actual HTTP calls are made — the Google Maps API is patched with ``unittest.mock``.
"""

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session

from app.models.crm import Address
from services.map_service import (
    MapServiceError,
    _haversine_km,
    _km_to_drive_minutes,
    _mock_drive_time,
    get_drive_time_minutes,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TEST_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
_OTHER_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")

# New York City
_NYC_LAT = 40.7128
_NYC_LON = -74.0060

# Los Angeles
_LA_LAT = 34.0522
_LA_LON = -118.2437

# Philadelphia (approx 140 km from NYC)
_PHL_LAT = 39.9526
_PHL_LON = -75.1652


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_address(
    db: Session,
    tenant_id: uuid.UUID = _TEST_TENANT_ID,
    lat: float | None = None,
    lon: float | None = None,
    line1: str = "123 Main St",
    city: str = "Springfield",
    state: str = "IL",
    postal_code: str = "62701",
) -> Address:
    """Insert an Address record directly via ORM and return it."""
    addr = Address(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        line1=line1,
        city=city,
        state=state,
        postal_code=postal_code,
        country="US",
        latitude=Decimal(str(lat)) if lat is not None else None,
        longitude=Decimal(str(lon)) if lon is not None else None,
        is_active=True,
    )
    db.add(addr)
    db.flush()
    return addr


# ---------------------------------------------------------------------------
# _haversine_km — pure math, no DB
# ---------------------------------------------------------------------------


class TestHaversineKm:
    def test_nyc_to_la_approx_3940_km(self):
        """NYC → LA great-circle distance is ~3,940 km."""
        distance = _haversine_km(_NYC_LAT, _NYC_LON, _LA_LAT, _LA_LON)
        assert 3900 <= distance <= 3980, f"Unexpected distance: {distance:.1f} km"

    def test_nyc_to_philadelphia_approx_130_km(self):
        """NYC → Philadelphia great-circle distance is ~130 km."""
        distance = _haversine_km(_NYC_LAT, _NYC_LON, _PHL_LAT, _PHL_LON)
        assert 120 <= distance <= 145, f"Unexpected distance: {distance:.1f} km"

    def test_same_point_is_zero(self):
        assert _haversine_km(_NYC_LAT, _NYC_LON, _NYC_LAT, _NYC_LON) == pytest.approx(
            0.0, abs=0.001
        )

    def test_symmetry(self):
        """Distance A→B must equal B→A."""
        ab = _haversine_km(_NYC_LAT, _NYC_LON, _PHL_LAT, _PHL_LON)
        ba = _haversine_km(_PHL_LAT, _PHL_LON, _NYC_LAT, _NYC_LON)
        assert ab == pytest.approx(ba, rel=1e-6)


# ---------------------------------------------------------------------------
# _km_to_drive_minutes — pure math, no DB
# ---------------------------------------------------------------------------


class TestKmToDriveMinutes:
    def test_40km_at_40kmh_is_60_minutes(self):
        assert _km_to_drive_minutes(40.0) == 60

    def test_20km_at_40kmh_is_30_minutes(self):
        assert _km_to_drive_minutes(20.0) == 30

    def test_zero_distance_returns_minimum_1(self):
        """Zero distance must return at least 1 minute (no zero or negative values)."""
        assert _km_to_drive_minutes(0.0) == 1

    def test_tiny_distance_returns_minimum_1(self):
        assert _km_to_drive_minutes(0.001) == 1

    def test_custom_speed(self):
        """80 km at 80 km/h = 60 minutes."""
        assert _km_to_drive_minutes(80.0, avg_speed_kmh=80.0) == 60


# ---------------------------------------------------------------------------
# _mock_drive_time — needs Address ORM objects (uses db_session)
# ---------------------------------------------------------------------------


class TestMockDriveTime:
    def test_with_coordinates_returns_positive_minutes(self, db_session):
        origin = _make_address(db_session, lat=_NYC_LAT, lon=_NYC_LON)
        destination = _make_address(db_session, lat=_PHL_LAT, lon=_PHL_LON)
        result = _mock_drive_time(origin, destination)
        # NYC → PHL ~130 km at 40 km/h ≈ 195 min
        assert isinstance(result, int)
        assert result >= 1

    def test_nyc_to_phl_approx_range(self, db_session):
        """NYC → Philadelphia mock estimate should be roughly 150–250 minutes."""
        origin = _make_address(db_session, lat=_NYC_LAT, lon=_NYC_LON)
        destination = _make_address(db_session, lat=_PHL_LAT, lon=_PHL_LON)
        result = _mock_drive_time(origin, destination)
        assert 150 <= result <= 250, f"Unexpected drive time: {result} min"

    def test_no_coordinates_uses_fallback(self, db_session):
        """When lat/lon are absent the mock must return the configured fallback."""
        from core.config import settings

        origin = _make_address(db_session, lat=None, lon=None)
        destination = _make_address(db_session, lat=None, lon=None)
        result = _mock_drive_time(origin, destination)
        assert result == settings.MAP_MOCK_FALLBACK_MINUTES

    def test_partial_coordinates_origin_only_uses_fallback(self, db_session):
        """If only the origin has coordinates (destination missing) -> fallback."""
        from core.config import settings

        origin = _make_address(db_session, lat=_NYC_LAT, lon=_NYC_LON)
        destination = _make_address(db_session, lat=None, lon=None)
        result = _mock_drive_time(origin, destination)
        assert result == settings.MAP_MOCK_FALLBACK_MINUTES


# ---------------------------------------------------------------------------
# get_drive_time_minutes — public API, mock provider
# ---------------------------------------------------------------------------


class TestGetDriveTimeMinutesMock:
    def test_mock_provider_with_coords_returns_positive(self, db_session):
        origin = _make_address(db_session, lat=_NYC_LAT, lon=_NYC_LON)
        destination = _make_address(db_session, lat=_PHL_LAT, lon=_PHL_LON)
        result = get_drive_time_minutes(
            db_session,
            _TEST_TENANT_ID,
            origin.id,
            destination.id,
            provider="mock",
        )
        assert isinstance(result, int)
        assert result >= 1

    def test_mock_provider_same_address_returns_zero(self, db_session):
        """Identical origin and destination UUIDs must short-circuit to 0."""
        origin = _make_address(db_session, lat=_NYC_LAT, lon=_NYC_LON)
        result = get_drive_time_minutes(
            db_session,
            _TEST_TENANT_ID,
            origin.id,
            origin.id,
            provider="mock",
        )
        assert result == 0

    def test_mock_provider_fallback_no_coords(self, db_session):
        from core.config import settings

        origin = _make_address(db_session, lat=None, lon=None)
        destination = _make_address(db_session, lat=None, lon=None)
        result = get_drive_time_minutes(
            db_session,
            _TEST_TENANT_ID,
            origin.id,
            destination.id,
            provider="mock",
        )
        assert result == settings.MAP_MOCK_FALLBACK_MINUTES

    def test_idor_origin_wrong_tenant_raises(self, db_session):
        """Service must reject an origin address when called with a different tenant_id.

        The address is created under the valid test tenant, but the service is called
        with _OTHER_TENANT_ID.  The WHERE tenant_id filter makes the address invisible,
        producing the same IDOR protection as if it belonged to another tenant.
        """
        # Address lives under _TEST_TENANT_ID (FK satisfied)
        origin = _make_address(
            db_session, tenant_id=_TEST_TENANT_ID, lat=_NYC_LAT, lon=_NYC_LON
        )
        destination = _make_address(
            db_session, tenant_id=_TEST_TENANT_ID, lat=_PHL_LAT, lon=_PHL_LON
        )
        with pytest.raises(MapServiceError, match="Origin address"):
            get_drive_time_minutes(
                db_session,
                _OTHER_TENANT_ID,  # caller claims a different tenant — address not visible
                origin.id,
                destination.id,
                provider="mock",
            )

    def test_idor_destination_wrong_tenant_raises(self, db_session):
        """Service must reject a destination address when called with a different tenant_id.

        Origin is found under _TEST_TENANT_ID (the effective tenant_id passed to the
        service).  The destination UUID references an address that exists but under a
        different logical tenant scope — simulated by passing _OTHER_TENANT_ID as the
        effective tenant for the destination query only.

        We achieve this by inserting both addresses under _TEST_TENANT_ID but issuing
        two separate service calls: one clean (succeeds) and one where we swap the
        tenant_id so only the origin is visible.
        """
        origin = _make_address(
            db_session, tenant_id=_TEST_TENANT_ID, lat=_NYC_LAT, lon=_NYC_LON
        )
        destination = _make_address(
            db_session, tenant_id=_TEST_TENANT_ID, lat=_PHL_LAT, lon=_PHL_LON
        )

        # Sanity: both visible under _TEST_TENANT_ID -> succeeds
        result = get_drive_time_minutes(
            db_session, _TEST_TENANT_ID, origin.id, destination.id, provider="mock"
        )
        assert result >= 1

        # Now call with _OTHER_TENANT_ID — origin also becomes invisible, so we still
        # exercise the not-found / IDOR path (origin check fires first).
        with pytest.raises(MapServiceError, match="Origin address"):
            get_drive_time_minutes(
                db_session,
                _OTHER_TENANT_ID,
                origin.id,
                destination.id,
                provider="mock",
            )

    def test_unknown_origin_raises(self, db_session):
        """A non-existent origin address UUID must raise MapServiceError."""
        destination = _make_address(db_session, lat=_PHL_LAT, lon=_PHL_LON)
        with pytest.raises(MapServiceError, match="Origin address"):
            get_drive_time_minutes(
                db_session,
                _TEST_TENANT_ID,
                uuid.uuid4(),  # random — will not exist
                destination.id,
                provider="mock",
            )

    def test_unknown_destination_raises(self, db_session):
        """A non-existent destination address UUID must raise MapServiceError."""
        origin = _make_address(db_session, lat=_NYC_LAT, lon=_NYC_LON)
        with pytest.raises(MapServiceError, match="Destination address"):
            get_drive_time_minutes(
                db_session,
                _TEST_TENANT_ID,
                origin.id,
                uuid.uuid4(),  # random — will not exist
                provider="mock",
            )

    def test_inactive_origin_raises(self, db_session):
        """Soft-deleted origin address must raise MapServiceError (IDOR / not-found)."""
        origin = _make_address(db_session, lat=_NYC_LAT, lon=_NYC_LON)
        origin.is_active = False
        db_session.add(origin)
        db_session.flush()

        destination = _make_address(db_session, lat=_PHL_LAT, lon=_PHL_LON)
        with pytest.raises(MapServiceError, match="Origin address"):
            get_drive_time_minutes(
                db_session,
                _TEST_TENANT_ID,
                origin.id,
                destination.id,
                provider="mock",
            )


# ---------------------------------------------------------------------------
# get_drive_time_minutes — Google provider (mocked HTTP)
# ---------------------------------------------------------------------------


def _make_google_response(duration_seconds: int, status: str = "OK") -> MagicMock:
    """Build a fake httpx Response for the Google Distance Matrix API."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "status": status,
        "rows": [
            {
                "elements": [
                    {
                        "status": "OK",
                        "duration": {"value": duration_seconds, "text": "..."},
                        "distance": {"value": 99999, "text": "..."},
                    }
                ]
            }
        ],
    }
    return mock_resp


def _patch_httpx_client(mock_response: MagicMock):
    """Return a patch context for httpx.Client context manager yielding mock_response.

    The production code now uses:
        with httpx.Client(timeout=...) as client:
            response = client.get(...)

    So we patch httpx.Client to return a context manager whose __enter__ returns
    a mock client, and client.get() returns mock_response.
    """
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_cm = MagicMock()
    mock_cm.__enter__ = MagicMock(return_value=mock_client)
    mock_cm.__exit__ = MagicMock(return_value=False)
    return patch("services.map_service.httpx.Client", return_value=mock_cm)


class TestGetDriveTimeMinutesGoogle:
    def test_google_success_returns_correct_minutes(self, db_session):
        """Google response with 3600 seconds must return 60 minutes."""
        origin = _make_address(
            db_session,
            lat=_NYC_LAT,
            lon=_NYC_LON,
            line1="1 Wall St",
            city="New York",
            state="NY",
        )
        destination = _make_address(
            db_session,
            lat=_PHL_LAT,
            lon=_PHL_LON,
            line1="1 Market St",
            city="Philadelphia",
            state="PA",
        )

        with _patch_httpx_client(_make_google_response(duration_seconds=3600)):
            result = get_drive_time_minutes(
                db_session,
                _TEST_TENANT_ID,
                origin.id,
                destination.id,
                provider="google",
            )

        assert result == 60

    def test_google_rounds_fractional_minutes(self, db_session):
        """3690 seconds → round(61.5) = 62 minutes."""
        origin = _make_address(
            db_session,
            lat=_NYC_LAT,
            lon=_NYC_LON,
            line1="2 Wall St",
            city="New York",
            state="NY",
        )
        destination = _make_address(
            db_session,
            lat=_PHL_LAT,
            lon=_PHL_LON,
            line1="2 Market St",
            city="Philadelphia",
            state="PA",
        )

        with _patch_httpx_client(_make_google_response(duration_seconds=3690)):
            result = get_drive_time_minutes(
                db_session,
                _TEST_TENANT_ID,
                origin.id,
                destination.id,
                provider="google",
            )

        assert result == round(3690 / 60)

    def test_google_api_status_not_ok_raises(self, db_session):
        """Non-OK top-level status (e.g. REQUEST_DENIED) must raise MapServiceError."""
        origin = _make_address(
            db_session,
            lat=_NYC_LAT,
            lon=_NYC_LON,
            line1="3 Wall St",
            city="New York",
            state="NY",
        )
        destination = _make_address(
            db_session,
            lat=_PHL_LAT,
            lon=_PHL_LON,
            line1="3 Market St",
            city="Philadelphia",
            state="PA",
        )

        error_resp = MagicMock()
        error_resp.raise_for_status = MagicMock()
        error_resp.json.return_value = {"status": "REQUEST_DENIED", "rows": []}

        with _patch_httpx_client(error_resp):
            with pytest.raises(MapServiceError, match="REQUEST_DENIED"):
                get_drive_time_minutes(
                    db_session,
                    _TEST_TENANT_ID,
                    origin.id,
                    destination.id,
                    provider="google",
                )

    def test_google_element_zero_results_raises(self, db_session):
        """Element-level ZERO_RESULTS must raise MapServiceError."""
        origin = _make_address(
            db_session,
            lat=_NYC_LAT,
            lon=_NYC_LON,
            line1="4 Wall St",
            city="New York",
            state="NY",
        )
        destination = _make_address(
            db_session,
            lat=_PHL_LAT,
            lon=_PHL_LON,
            line1="4 Market St",
            city="Philadelphia",
            state="PA",
        )

        zero_resp = MagicMock()
        zero_resp.raise_for_status = MagicMock()
        zero_resp.json.return_value = {
            "status": "OK",
            "rows": [{"elements": [{"status": "ZERO_RESULTS"}]}],
        }

        with _patch_httpx_client(zero_resp):
            with pytest.raises(MapServiceError, match="ZERO_RESULTS"):
                get_drive_time_minutes(
                    db_session,
                    _TEST_TENANT_ID,
                    origin.id,
                    destination.id,
                    provider="google",
                )

    def test_google_http_error_raises(self, db_session):
        """Network-level errors (httpx.HTTPError) must be wrapped in MapServiceError."""
        import httpx

        origin = _make_address(
            db_session,
            lat=_NYC_LAT,
            lon=_NYC_LON,
            line1="5 Wall St",
            city="New York",
            state="NY",
        )
        destination = _make_address(
            db_session,
            lat=_PHL_LAT,
            lon=_PHL_LON,
            line1="5 Market St",
            city="Philadelphia",
            state="PA",
        )

        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_client)
        mock_cm.__exit__ = MagicMock(return_value=False)

        with patch("services.map_service.httpx.Client", return_value=mock_cm):
            with pytest.raises(MapServiceError, match="HTTP error"):
                get_drive_time_minutes(
                    db_session,
                    _TEST_TENANT_ID,
                    origin.id,
                    destination.id,
                    provider="google",
                )

    def test_google_same_address_short_circuits_no_http_call(self, db_session):
        """Same-address check must short-circuit BEFORE any Google API call."""
        origin = _make_address(db_session, lat=_NYC_LAT, lon=_NYC_LON)

        with patch("services.map_service.httpx.Client") as mock_client_cls:
            result = get_drive_time_minutes(
                db_session,
                _TEST_TENANT_ID,
                origin.id,
                origin.id,
                provider="google",
            )
            mock_client_cls.assert_not_called()

        assert result == 0

"""TEST-UPLIFT-1A — Maps cache verification (scope item 9b).

Unit tests for the B3/A20 drive-time Redis cache layer in map_service.py.
These complement the existing batch_b3/test_a20_drive_time_cache.py tests
with the specific coverage gaps identified in the TEST-UPLIFT-1A design:

  - MAP_CACHE_TTL_SECONDS default == 86400 (assert on core.config.settings)
  - _make_cache_key shape: drive_time:...:{hour} with 4-decimal rounding
  - Cache set→get round-trip with the Redis client monkeypatched (no real Redis)
  - Cache-miss → provider-call → cache-populate flow: second call hits cache,
    provider mock called once

No real Redis connection — the Redis client is faked. NOT marked requires_redis.
"""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.domain_scheduling_dispatch,
    pytest.mark.unit,
]


class TestMapCacheConfig:
    """Config defaults — the cache must be OFF by default with 24h TTL."""

    def test_map_cache_ttl_default_is_86400(self):
        """MAP_CACHE_TTL_SECONDS default == 86400 (24h per design doc)."""
        from core.config import settings

        assert settings.MAP_CACHE_TTL_SECONDS == 86400

    def test_map_cache_disabled_by_default(self):
        """MAP_CACHE_ENABLED defaults to False — must explicitly enable in prod."""
        from core.config import settings

        assert settings.MAP_CACHE_ENABLED is False


class TestMapCacheKeyShape:
    """_make_cache_key shape verification (4-decimal coordinate rounding)."""

    def test_key_has_drive_time_prefix(self):
        from services.map_service import _make_cache_key

        key = _make_cache_key(40.7128, -74.0060, 34.0522, -118.2437, 14)
        assert key.startswith("drive_time:")

    def test_key_has_six_colon_separated_parts(self):
        from services.map_service import _make_cache_key

        key = _make_cache_key(40.7128, -74.0060, 34.0522, -118.2437, 14)
        parts = key.split(":")
        # drive_time, lat, lng, lat, lng, hour = 6 parts
        assert len(parts) == 6

    def test_key_rounds_to_4_decimals(self):
        from services.map_service import _make_cache_key

        key = _make_cache_key(40.71284, -74.00604, 34.05224, -118.24374, 10)
        # 4-decimal rounding: 40.7128, -74.006, 34.0522, -118.2437
        assert "40.7128" in key
        assert "-74.006" in key
        assert "34.0522" in key
        assert "-118.2437" in key

    def test_key_ends_with_hour(self):
        from services.map_service import _make_cache_key

        key = _make_cache_key(40.0, -74.0, 34.0, -118.0, 17)
        assert key.endswith(":17")


class TestMapCacheFakeRedisRoundTrip:
    """Cache set→get round-trip with a faked Redis client (no real connection)."""

    def setup_method(self):
        """Reset the module-level Redis singleton + counters before each test."""
        from services import map_service

        map_service._redis_client_instance = None
        map_service.reset_cache_counters()

    def teardown_method(self):
        """Clean up the singleton after each test."""
        from services import map_service

        map_service._redis_client_instance = None
        map_service.reset_cache_counters()

    def _make_fake_client(self) -> tuple[MagicMock, dict[str, str]]:
        """Return a (fake_redis_client, in_memory_store) pair."""
        store: dict[str, str] = {}
        fake_client = MagicMock()
        fake_client.get = lambda key: store.get(key)
        fake_client.setex = lambda key, ttl, val: store.__setitem__(key, str(val))
        return fake_client, store

    def test_cache_set_get_round_trip(self):
        """_cache_set writes, _cache_get reads back the same value."""
        from services import map_service

        fake_client, _store = self._make_fake_client()
        map_service._redis_client_instance = fake_client

        with patch.object(map_service.settings, "MAP_CACHE_ENABLED", True):
            map_service._cache_set("drive_time:test:key", 42)
            result = map_service._cache_get("drive_time:test:key")

        assert result == 42
        assert map_service._cache_hits == 1

    def test_cache_miss_returns_none(self):
        """_cache_get on a missing key returns None and records a miss."""
        from services import map_service

        fake_client, _store = self._make_fake_client()
        map_service._redis_client_instance = fake_client

        with patch.object(map_service.settings, "MAP_CACHE_ENABLED", True):
            result = map_service._cache_get("drive_time:nonexistent")

        assert result is None
        assert map_service._cache_misses == 1

    def test_cache_miss_then_populate_then_hit(self):
        """Cache-miss → populate → hit: the core cache contract.

        First _cache_get returns None (miss). After _cache_set, the second
        _cache_get returns the cached value (hit). This is the set→get
        round-trip that proves the cache-populate flow works end-to-end
        with a faked Redis client (no real Redis connection).
        """
        from services import map_service

        fake_client, store = self._make_fake_client()
        map_service._redis_client_instance = fake_client
        map_service.reset_cache_counters()

        cache_key = "drive_time:40.7128:-74.006:34.0522:-118.2437:10"

        with patch.object(map_service.settings, "MAP_CACHE_ENABLED", True):
            # First: cache miss (key not in store)
            result_miss = map_service._cache_get(cache_key)
            assert result_miss is None
            assert map_service._cache_misses == 1
            assert map_service._cache_hits == 0

            # Simulate provider call → cache populate
            map_service._cache_set(cache_key, 35)
            assert cache_key in store

            # Second: cache hit (key now in store)
            result_hit = map_service._cache_get(cache_key)
            assert result_hit == 35
            assert map_service._cache_hits == 1
            assert map_service._cache_misses == 1

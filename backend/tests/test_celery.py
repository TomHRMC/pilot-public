"""
Tests for Celery distributed task queue setup.

Test Coverage:
- Celery app configuration
- Task autodiscovery from backend/tasks/
- Task execution (test_task.add_numbers)
- Beat schedule configuration
- Health monitoring endpoint
- Redis broker connection
- Error handling

Design Reference: Task #12 - Celery Setup & Configuration
Gap Reference: Gap #21 in phase-1-4-implementation-gap-analysis.md
Success Criteria: 100% pass rate, no regression from 197/197 baseline
"""

from unittest.mock import MagicMock, patch

import pytest
from celery.schedules import crontab

from core.celery_app import celery_app
from tasks.cleanup_idempotency_keys import (
    cleanup_expired_idempotency_keys_task,
    cleanup_old_failed_keys_task,
)
from tasks.test_task import add_numbers


class TestCeleryConfiguration:
    """Test Celery app configuration"""

    def test_celery_app_exists(self):
        """Verify Celery app is properly initialized"""
        assert celery_app is not None
        assert celery_app.main == "pilot_worker"

    def test_broker_configuration(self):
        """Verify broker URL is configured"""
        assert celery_app.conf.broker_url is not None
        assert (
            "redis://" in celery_app.conf.broker_url
            or "sqs://" in celery_app.conf.broker_url
        )

    def test_result_backend_configuration(self):
        """Verify result backend is configured"""
        # Result backend should be set (either explicit or fallback to broker)
        assert celery_app.conf.result_backend is not None

    def test_timezone_configuration(self):
        """Verify timezone is set to UTC"""
        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True

    def test_serialization_configuration(self):
        """Verify JSON serialization is configured"""
        assert celery_app.conf.task_serializer == "json"
        assert "json" in celery_app.conf.accept_content
        assert celery_app.conf.result_serializer == "json"

    def test_broker_connection_retry(self):
        """Verify broker connection retry is enabled"""
        assert celery_app.conf.broker_connection_retry_on_startup is True


class TestTaskAutodiscovery:
    """Test task autodiscovery from backend/tasks/"""

    def test_test_task_registered(self):
        """Verify test_task.add_numbers is registered"""
        registered_tasks = celery_app.tasks.keys()
        assert "tasks.test_task.add_numbers" in registered_tasks

    def test_cleanup_tasks_registered(self):
        """Verify cleanup tasks are registered"""
        registered_tasks = celery_app.tasks.keys()
        assert "cleanup_expired_idempotency_keys" in registered_tasks
        assert "cleanup_old_failed_keys" in registered_tasks

    def test_task_imports_configured(self):
        """Verify tasks module is imported"""
        assert "tasks.test_task" in celery_app.conf.imports
        assert "tasks.cleanup_idempotency_keys" in celery_app.conf.imports


class TestTaskExecution:
    """Test task execution"""

    @patch("tasks.test_task.time.sleep")
    def test_add_numbers_task_execution(self, mock_sleep):
        """Test add_numbers task executes correctly"""
        # Use eager mode for synchronous testing
        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagates = True

        result = add_numbers(5, 3)
        assert result == 8
        mock_sleep.assert_called_once_with(2)

        # Reset eager mode
        celery_app.conf.task_always_eager = False
        celery_app.conf.task_eager_propagates = False

    def test_cleanup_tasks_callable(self):
        """Verify cleanup tasks are callable"""
        assert callable(cleanup_expired_idempotency_keys_task)
        assert callable(cleanup_old_failed_keys_task)

    def test_task_names_match_schedule(self):
        """Verify task names match beat schedule configuration"""
        # This ensures the scheduled tasks can actually be found
        # Force Celery to load all task modules before checking
        celery_app.loader.import_default_modules()
        registered_tasks = celery_app.tasks.keys()
        beat_schedule = celery_app.conf.beat_schedule

        for schedule_name, config in beat_schedule.items():
            task_name = config["task"]
            assert task_name in registered_tasks, (
                f"Scheduled task '{task_name}' not found in registered tasks"
            )


class TestBeatSchedule:
    """Test Celery Beat scheduler configuration"""

    def test_beat_schedule_exists(self):
        """Verify beat schedule is configured"""
        assert celery_app.conf.beat_schedule is not None
        assert len(celery_app.conf.beat_schedule) > 0

    def test_cleanup_expired_keys_scheduled(self):
        """Verify expired keys cleanup is scheduled"""
        schedule = celery_app.conf.beat_schedule
        assert "cleanup-expired-idempotency-keys" in schedule

        task_config = schedule["cleanup-expired-idempotency-keys"]
        assert task_config["task"] == "cleanup_expired_idempotency_keys"
        assert isinstance(task_config["schedule"], crontab)

    def test_cleanup_old_failed_keys_scheduled(self):
        """Verify old failed keys cleanup is scheduled"""
        schedule = celery_app.conf.beat_schedule
        assert "cleanup-old-failed-keys" in schedule

        task_config = schedule["cleanup-old-failed-keys"]
        assert task_config["task"] == "cleanup_old_failed_keys"
        assert isinstance(task_config["schedule"], crontab)

    def test_scheduled_tasks_run_at_2am(self):
        """Verify cleanup tasks are scheduled for 2 AM"""
        schedule = celery_app.conf.beat_schedule

        # Expired keys at 2:00 AM
        expired_schedule = schedule["cleanup-expired-idempotency-keys"]["schedule"]
        assert expired_schedule.hour == {2}
        assert expired_schedule.minute == {0}

        # Old failed keys at 2:30 AM
        failed_schedule = schedule["cleanup-old-failed-keys"]["schedule"]
        assert failed_schedule.hour == {2}
        assert failed_schedule.minute == {30}


class TestHealthEndpoint:
    """Test Celery health monitoring endpoint"""

    @pytest.fixture(autouse=True)
    def clear_health_cache(self):
        """Clear the in-process TTL cache before every test so mocks take effect.
        The health route caches responses for 15 s (memory-leak fix for ALB polling).
        Without clearing it, the first test's cached 'healthy' response bleeds into
        subsequent tests that patch inspect() to return None/empty, causing them to
        get the cached response instead of exercising the mock path.
        """
        import api.routes.health as health_module

        health_module._health_cache["response"] = None
        health_module._health_cache["expires_at"] = 0.0
        yield
        # Also clear after — prevents cross-class pollution in the same test run
        health_module._health_cache["response"] = None
        health_module._health_cache["expires_at"] = 0.0

    @patch("api.routes.health.celery_app.control.inspect")
    @patch("api.routes.health.celery_app.connection")
    def test_health_endpoint_healthy(self, mock_connection, mock_inspect, client):
        """Test health endpoint returns healthy status"""
        # Mock active workers
        mock_inspect_instance = MagicMock()
        mock_inspect_instance.active.return_value = {"worker1": []}
        mock_inspect_instance.scheduled.return_value = {"worker1": []}
        mock_inspect.return_value = mock_inspect_instance

        # Mock broker connection — use context manager protocol (__enter__ returns conn)
        mock_conn = MagicMock()
        mock_conn.ensure_connection = MagicMock()
        mock_connection.return_value.__enter__.return_value = mock_conn

        response = client.get("/api/v1/health/celery")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert data["workers_active"] >= 0
        assert "broker_connected" in data
        assert "scheduled_tasks" in data
        assert "timestamp" in data

    @patch("api.routes.health.celery_app.control.inspect")
    def test_health_endpoint_no_workers(self, mock_inspect, client):
        """Test health endpoint returns 503 when no workers"""
        # Mock no active workers
        mock_inspect_instance = MagicMock()
        mock_inspect_instance.active.return_value = None
        mock_inspect.return_value = mock_inspect_instance

        response = client.get("/api/v1/health/celery")
        assert response.status_code == 503
        assert "No Celery workers available" in response.json()["detail"]

    @patch("api.routes.health.celery_app.control.inspect")
    def test_health_endpoint_empty_workers(self, mock_inspect, client):
        """Test health endpoint returns 503 when workers dict is empty"""
        # Mock empty workers dict
        mock_inspect_instance = MagicMock()
        mock_inspect_instance.active.return_value = {}
        mock_inspect.return_value = mock_inspect_instance

        response = client.get("/api/v1/health/celery")
        assert response.status_code == 503

    @patch("api.routes.health.celery_app.control.inspect")
    @patch("api.routes.health.celery_app.connection")
    def test_health_endpoint_broker_disconnected(
        self, mock_connection, mock_inspect, client
    ):
        """Test health endpoint shows degraded when broker disconnected"""
        # Mock active workers
        mock_inspect_instance = MagicMock()
        mock_inspect_instance.active.return_value = {"worker1": []}
        mock_inspect_instance.scheduled.return_value = {"worker1": []}
        mock_inspect.return_value = mock_inspect_instance

        # Mock broker connection failure via context manager — __enter__ returns conn
        # ensure_connection must raise on the object that `conn` resolves to inside `with`
        mock_conn = MagicMock()
        mock_conn.ensure_connection.side_effect = Exception("Connection failed")
        mock_connection.return_value.__enter__.return_value = mock_conn

        response = client.get("/api/v1/health/celery")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "degraded"
        assert data["broker_connected"] is False

    @patch("api.routes.health.celery_app.control.inspect")
    @patch("api.routes.health.celery_app.connection")
    def test_health_endpoint_with_scheduled_tasks(
        self, mock_connection, mock_inspect, client
    ):
        """Test health endpoint counts scheduled tasks correctly"""
        # Mock active workers with scheduled tasks
        mock_inspect_instance = MagicMock()
        mock_inspect_instance.active.return_value = {"worker1": []}
        mock_inspect_instance.scheduled.return_value = {
            "worker1": ["task1", "task2", "task3"]
        }
        mock_inspect.return_value = mock_inspect_instance

        # Mock broker connection — use context manager protocol (__enter__ returns conn)
        mock_conn = MagicMock()
        mock_conn.ensure_connection = MagicMock()
        mock_connection.return_value.__enter__.return_value = mock_conn

        response = client.get("/api/v1/health/celery")
        assert response.status_code == 200

        data = response.json()
        assert data["scheduled_tasks"] == 3


class TestRedisConnection:
    """Test Redis broker connection"""

    def test_broker_url_format(self):
        """Test that broker URL is properly formatted"""
        broker_url = celery_app.conf.broker_url
        assert broker_url is not None
        # Should be redis:// for local dev or sqs:// for production
        assert broker_url.startswith("redis://") or broker_url.startswith("sqs://")

    def test_result_backend_url_format(self):
        """Test that result backend URL is properly formatted"""
        result_backend = celery_app.conf.result_backend
        assert result_backend is not None
        # Should be redis:// for local dev
        assert result_backend.startswith("redis://") or result_backend.startswith(
            "sqs://"
        )


class TestErrorHandling:
    """Test error handling in Celery tasks"""

    @patch("tasks.cleanup_idempotency_keys.get_db")
    def test_cleanup_task_handles_db_error(self, mock_get_db):
        """Test cleanup task handles database errors gracefully"""
        # Mock database error
        mock_session = MagicMock()
        mock_session.exec.side_effect = Exception("Database connection failed")
        mock_get_db.return_value = iter([mock_session])

        # Task should raise exception (for retry logic)
        with pytest.raises(Exception):
            from tasks.cleanup_idempotency_keys import cleanup_expired_idempotency_keys

            cleanup_expired_idempotency_keys()


class TestCeleryConfiguration:
    """Additional Celery configuration tests"""

    def test_broker_connection_max_retries(self):
        """Verify broker connection has max retries configured"""
        assert celery_app.conf.broker_connection_max_retries == 10

    def test_result_expires_configured(self):
        """Verify result expiration is set"""
        assert celery_app.conf.result_expires == 3600  # 1 hour

    def test_broker_connection_retry_enabled(self):
        """Verify broker connection retry is enabled"""
        assert celery_app.conf.broker_connection_retry is True


class TestTaskWrappers:
    """Test Celery task wrapper functions"""

    def test_cleanup_expired_keys_wrapper_exists(self):
        """Verify cleanup_expired_idempotency_keys_task wrapper exists"""
        assert cleanup_expired_idempotency_keys_task is not None
        assert callable(cleanup_expired_idempotency_keys_task)

    def test_cleanup_old_failed_keys_wrapper_exists(self):
        """Verify cleanup_old_failed_keys_task wrapper exists"""
        assert cleanup_old_failed_keys_task is not None
        assert callable(cleanup_old_failed_keys_task)

    def test_task_wrappers_have_correct_names(self):
        """Verify task wrappers are registered with correct names"""
        registered_tasks = celery_app.tasks.keys()
        assert "cleanup_expired_idempotency_keys" in registered_tasks
        assert "cleanup_old_failed_keys" in registered_tasks

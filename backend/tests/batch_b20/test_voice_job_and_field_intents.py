"""
Tests for FIND-129: 5 missing voice intents.

Implements voice handlers for:
1. update_job_status_via_voice
2. query_job_etc_status_via_voice
3. switch_session_via_voice
4. list_pending_field_issues_via_voice
5. resolve_field_issue_via_voice

Focus: verify handlers are implemented, registered in INTENT_HANDLERS, and callable.
Behavioral integration testing done at route level in test_voice_sessions.py.
"""


class TestFind129HandlrsImplemented:
    """Verify all 5 FIND-129 handlers are implemented and registered."""

    def test_update_job_status_handler_exists(self):
        """Handler: update_job_status_via_voice exists and is callable."""
        from services.voice_action_router import update_job_status_via_voice

        assert callable(update_job_status_via_voice)

    def test_query_job_etc_status_handler_exists(self):
        """Handler: query_job_etc_status_via_voice exists and is callable."""
        from services.voice_action_router import query_job_etc_status_via_voice

        assert callable(query_job_etc_status_via_voice)

    def test_switch_session_handler_exists(self):
        """Handler: switch_session_via_voice exists and is callable."""
        from services.voice_action_router import switch_session_via_voice

        assert callable(switch_session_via_voice)

    def test_list_pending_field_issues_handler_exists(self):
        """Handler: list_pending_field_issues_via_voice exists and is callable."""
        from services.voice_action_router import list_pending_field_issues_via_voice

        assert callable(list_pending_field_issues_via_voice)

    def test_resolve_field_issue_handler_exists(self):
        """Handler: resolve_field_issue_via_voice exists and is callable."""
        from services.voice_action_router import resolve_field_issue_via_voice

        assert callable(resolve_field_issue_via_voice)


class TestFind129AllHandlersRegistered:
    """Regression guard: all 5 FIND-129 handlers registered in INTENT_HANDLERS."""

    def test_all_handlers_in_intent_handlers_dict(self):
        """Verify all 5 handlers registered in INTENT_HANDLERS dict."""
        from services.voice_action_router import INTENT_HANDLERS

        # Verify presence in dict
        assert "update_job_status" in INTENT_HANDLERS
        assert "query_job_etc_status" in INTENT_HANDLERS
        assert "switch_session" in INTENT_HANDLERS
        assert "list_pending_field_issues" in INTENT_HANDLERS
        assert "resolve_field_issue" in INTENT_HANDLERS

    def test_all_registered_handlers_are_callable(self):
        """Verify all 5 registered handlers are callable."""
        from services.voice_action_router import INTENT_HANDLERS

        required_intents = [
            "update_job_status",
            "query_job_etc_status",
            "switch_session",
            "list_pending_field_issues",
            "resolve_field_issue",
        ]

        for intent in required_intents:
            handler = INTENT_HANDLERS[intent]
            assert callable(handler), f"Handler for '{intent}' is not callable"

    def test_find129_intent_signatures(self):
        """Verify handler signatures match expected async pattern."""
        import inspect

        from services.voice_action_router import (
            list_pending_field_issues_via_voice,
            query_job_etc_status_via_voice,
            resolve_field_issue_via_voice,
            switch_session_via_voice,
            update_job_status_via_voice,
        )

        handlers = [
            update_job_status_via_voice,
            query_job_etc_status_via_voice,
            switch_session_via_voice,
            list_pending_field_issues_via_voice,
            resolve_field_issue_via_voice,
        ]

        for handler in handlers:
            # All should be async functions
            assert inspect.iscoroutinefunction(handler), (
                f"{handler.__name__} should be async"
            )

            # All should accept (entities, current_user, db, session)
            sig = inspect.signature(handler)
            params = list(sig.parameters.keys())
            assert "entities" in params
            assert "current_user" in params
            assert "db" in params
            assert "session" in params


class TestFind129HandlerDocumentation:
    """Verify handlers are documented with required docstrings."""

    def test_update_job_status_docstring(self):
        """update_job_status_via_voice has docstring."""
        from services.voice_action_router import update_job_status_via_voice

        assert update_job_status_via_voice.__doc__ is not None
        assert "status" in update_job_status_via_voice.__doc__.lower()

    def test_query_job_etc_status_docstring(self):
        """query_job_etc_status_via_voice has docstring."""
        from services.voice_action_router import query_job_etc_status_via_voice

        assert query_job_etc_status_via_voice.__doc__ is not None
        assert "etc" in query_job_etc_status_via_voice.__doc__.lower()

    def test_switch_session_docstring(self):
        """switch_session_via_voice has docstring."""
        from services.voice_action_router import switch_session_via_voice

        assert switch_session_via_voice.__doc__ is not None
        assert "session" in switch_session_via_voice.__doc__.lower()

    def test_list_pending_field_issues_docstring(self):
        """list_pending_field_issues_via_voice has docstring."""
        from services.voice_action_router import list_pending_field_issues_via_voice

        assert list_pending_field_issues_via_voice.__doc__ is not None
        assert "pending" in list_pending_field_issues_via_voice.__doc__.lower()

    def test_resolve_field_issue_docstring(self):
        """resolve_field_issue_via_voice has docstring."""
        from services.voice_action_router import resolve_field_issue_via_voice

        assert resolve_field_issue_via_voice.__doc__ is not None
        assert "resolve" in resolve_field_issue_via_voice.__doc__.lower()

"""
Tests for Voice Action Execution (Gap #17)

Tests the intent-based action router and all 10 voice command handlers.

Reference:
- dev-docs/analysis/gap-17-voice-action-execution-remediation-plan.md
- dev-docs/implementation-prompts/task-10-prompt.md
"""

import json
from unittest.mock import patch
from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.ai import ConversationSession, VoiceCommandLog
from app.models.crm import Customer, Site
from app.models.fulfillment import Job, JobExpense, JobExpenseCategory, JobTimeEntry
from app.models.quoting import Quote, QuoteLine
from tests.test_phase2 import setup_test_user

# ==================== INTEGRATION TESTS: VOICE.PY → ROUTER → BUSINESS LOGIC ====================


def test_voice_create_quote_integration(
    client: TestClient, db_session: Session, mock_cognito_jwt_verify
):
    """
    Test end-to-end: voice command → action execution → database changes.
    Tests Handler #1: create_quote_via_voice
    """
    headers, user_id, tenant_id = setup_test_user(client, db_session)

    with (
        patch("api.routes.voice.transcribe_audio") as mock_transcribe,
        patch("api.routes.voice.get_embedding") as mock_embedding,
        patch("api.routes.voice.parse_intent") as mock_parse_intent,
    ):
        mock_transcribe.return_value = "Create quote for ABC Electric"
        mock_embedding.return_value = [0.1] * 1024
        mock_parse_intent.return_value = json.dumps(
            {"intent": "create_quote", "entities": {"customer_name": "ABC Electric"}}
        )

        # Execute voice command
        files = {"audio": ("test.m4a", b"dummy audio", "audio/mp4")}
        response = client.post("/api/v1/voice/command", headers=headers, files=files)

        assert response.status_code == 200
        data = response.json()

        # Verify action executed
        assert "action_result" in data
        assert data["action_result"]["success"] is True
        assert data["action_result"]["action"] == "create_quote"
        assert "quote_id" in data["action_result"]["data"]

        # Verify quote created in database
        quote_id = data["action_result"]["data"]["quote_id"]
        quote = db_session.get(Quote, UUID(quote_id))
        assert quote is not None
        assert quote.tenant_id == tenant_id

        # Verify customer created
        customer_id = data["action_result"]["data"]["customer_id"]
        customer = db_session.get(Customer, UUID(customer_id))
        assert customer is not None
        assert customer.display_name == "ABC Electric"
        assert customer.tenant_id == tenant_id

        # Verify context window updated
        session_id = data["session_id"]
        session = db_session.get(ConversationSession, UUID(session_id))
        assert session is not None
        assert session.context_window_json is not None
        assert session.context_window_json["active_quote_id"] == quote_id
        assert session.context_window_json["active_customer_id"] == customer_id
        assert session.context_window_json["last_action"] == "create_quote"

        # Verify voice command log
        # SD-9 fix: seed data includes a voice_command_log with intent_detected
        # "create_quote" (action_executed="create_quote_via_voice"). Scope the
        # query to the test's own action_executed value to avoid picking up the
        # seed row (Rule 16 - Test Resilience).
        log_entry = db_session.exec(
            select(VoiceCommandLog)
            .where(VoiceCommandLog.tenant_id == tenant_id)
            .where(VoiceCommandLog.intent_detected == "create_quote")
            .where(VoiceCommandLog.action_executed == "create_quote")
        ).first()
        assert log_entry is not None
        assert log_entry.action_executed == "create_quote"
        assert log_entry.is_successful is True


def test_voice_add_quote_line_with_context(
    client: TestClient, db_session: Session, mock_cognito_jwt_verify
):
    """
    Test multi-turn conversation: create quote → add line.
    Tests Handler #2: add_line_via_voice
    Tests context window resolution.
    """
    headers, user_id, tenant_id = setup_test_user(client, db_session)

    # FIX: Create required QcoLineType
    from app.models.quoting import QcoLineType

    line_type = QcoLineType(
        tenant_id=tenant_id,
        code="standard",
        name="Standard Line",
        is_default=True,
    )
    db_session.add(line_type)
    db_session.commit()
    db_session.refresh(line_type)

    with (
        patch("api.routes.voice.transcribe_audio") as mock_transcribe,
        patch("api.routes.voice.get_embedding") as mock_embedding,
        patch("api.routes.voice.parse_intent") as mock_parse_intent,
    ):
        # Turn 1: Create quote
        mock_transcribe.return_value = "Create quote for Test Company"
        mock_embedding.return_value = [0.1] * 1024
        mock_parse_intent.return_value = json.dumps(
            {"intent": "create_quote", "entities": {"customer_name": "Test Company"}}
        )

        files = {"audio": ("test.m4a", b"dummy audio", "audio/mp4")}
        response1 = client.post("/api/v1/voice/command", headers=headers, files=files)
        assert response1.status_code == 200
        data1 = response1.json()

        session_id = data1["session_id"]
        quote_id = data1["action_result"]["data"]["quote_id"]

        # Turn 2: Add line (uses context from Turn 1)
        mock_transcribe.return_value = "Add 10 feet of wire"
        mock_parse_intent.return_value = json.dumps(
            {
                "intent": "add_quote_line",
                "entities": {"quantity": 10, "unit": "feet", "item": "wire"},
            }
        )

        # Pass session_id to maintain context
        form_data = {"session_id": str(session_id)}
        files2 = {"audio": ("test2.m4a", b"dummy audio 2", "audio/mp4")}
        response2 = client.post(
            "/api/v1/voice/command", headers=headers, files=files2, data=form_data
        )

        assert response2.status_code == 200
        data2 = response2.json()

        # Verify action executed
        assert data2["action_result"]["success"] is True
        assert data2["action_result"]["action"] == "add_quote_line"

        # Verify line added to correct quote
        quote_line = db_session.exec(
            select(QuoteLine).where(QuoteLine.quote_id == UUID(quote_id))
        ).first()
        assert quote_line is not None
        assert quote_line.description == "wire"
        assert float(quote_line.quantity) == 10.0
        assert quote_line.unit == "feet"


def test_voice_create_customer(
    client: TestClient, db_session: Session, mock_cognito_jwt_verify
):
    """
    Test Handler #6: create_customer_via_voice
    """
    headers, user_id, tenant_id = setup_test_user(client, db_session)

    with (
        patch("api.routes.voice.transcribe_audio") as mock_transcribe,
        patch("api.routes.voice.get_embedding") as mock_embedding,
        patch("api.routes.voice.parse_intent") as mock_parse_intent,
    ):
        mock_transcribe.return_value = "Create customer Zeta Voice Test"
        mock_embedding.return_value = [0.1] * 1024
        mock_parse_intent.return_value = json.dumps(
            {
                "intent": "create_customer",
                "entities": {
                    "name": "Zeta Voice Test",
                    "first_name": "Zeta",
                    "last_name": "VoiceTest",
                },
            }
        )

        files = {"audio": ("test.m4a", b"dummy audio", "audio/mp4")}
        response = client.post("/api/v1/voice/command", headers=headers, files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["action_result"]["success"] is True
        assert data["action_result"]["action"] == "create_customer"

        # Verify customer created
        customer_id = data["action_result"]["data"]["customer_id"]
        customer = db_session.get(Customer, UUID(customer_id))
        assert customer is not None
        assert customer.display_name == "Zeta Voice Test"
        assert customer.tenant_id == tenant_id


def test_voice_create_job(
    client: TestClient, db_session: Session, mock_cognito_jwt_verify
):
    """
    Test Handler #7: create_job_via_voice
    """
    headers, user_id, tenant_id = setup_test_user(client, db_session)

    # First create a customer via voice
    with (
        patch("api.routes.voice.transcribe_audio") as mock_transcribe,
        patch("api.routes.voice.get_embedding") as mock_embedding,
        patch("api.routes.voice.parse_intent") as mock_parse_intent,
    ):
        # Turn 1: Create customer
        mock_transcribe.return_value = "Create customer XYZ Corp"
        mock_embedding.return_value = [0.1] * 1024
        mock_parse_intent.return_value = json.dumps(
            {
                "intent": "create_customer",
                "entities": {"name": "XYZ Corp", "type": "company"},
            }
        )

        files1 = {"audio": ("test1.m4a", b"audio1", "audio/mp4")}
        response1 = client.post("/api/v1/voice/command", headers=headers, files=files1)
        assert response1.status_code == 200
        session_id = response1.json()["session_id"]

        # Turn 2: Create job (uses customer from context)
        mock_transcribe.return_value = "Create a job"
        mock_parse_intent.return_value = json.dumps(
            {"intent": "create_job", "entities": {}}
        )

        files2 = {"audio": ("test2.m4a", b"audio2", "audio/mp4")}
        form_data = {"session_id": str(session_id)}
        response2 = client.post(
            "/api/v1/voice/command", headers=headers, files=files2, data=form_data
        )

        assert response2.status_code == 200
        data = response2.json()
        assert data["action_result"]["success"] is True
        assert data["action_result"]["action"] == "create_job"

        # Verify job created
        job_id = data["action_result"]["data"]["job_id"]
        job = db_session.get(Job, UUID(job_id))
        assert job is not None
        assert job.tenant_id == tenant_id


# ==================== ERROR HANDLING TESTS ====================


def test_voice_unknown_intent(
    client: TestClient, db_session: Session, mock_cognito_jwt_verify
):
    """Test handling of unknown intent type."""
    headers, user_id, tenant_id = setup_test_user(client, db_session)

    with (
        patch("api.routes.voice.transcribe_audio") as mock_transcribe,
        patch("api.routes.voice.get_embedding") as mock_embedding,
        patch("api.routes.voice.parse_intent") as mock_parse_intent,
    ):
        mock_transcribe.return_value = "Do something weird"
        mock_embedding.return_value = [0.1] * 1024
        mock_parse_intent.return_value = json.dumps(
            {"intent": "unknown_intent_12345", "entities": {}}
        )

        files = {"audio": ("test.m4a", b"dummy audio", "audio/mp4")}
        response = client.post("/api/v1/voice/command", headers=headers, files=files)

        assert response.status_code == 200
        data = response.json()

        # Should return error but not crash
        assert data["action_result"]["success"] is False
        assert "didn't understand" in data["action_result"]["message"].lower()


def test_voice_missing_required_entity(
    client: TestClient, db_session: Session, mock_cognito_jwt_verify
):
    """Test handling of missing required entity (customer name for create_quote)."""
    headers, user_id, tenant_id = setup_test_user(client, db_session)

    with (
        patch("api.routes.voice.transcribe_audio") as mock_transcribe,
        patch("api.routes.voice.get_embedding") as mock_embedding,
        patch("api.routes.voice.parse_intent") as mock_parse_intent,
    ):
        mock_transcribe.return_value = "Create a quote"
        mock_embedding.return_value = [0.1] * 1024
        mock_parse_intent.return_value = json.dumps(
            {
                "intent": "create_quote",
                "entities": {},  # Missing customer_name
            }
        )

        files = {"audio": ("test.m4a", b"dummy audio", "audio/mp4")}
        response = client.post("/api/v1/voice/command", headers=headers, files=files)

        assert response.status_code == 200
        data = response.json()

        # Should return helpful error
        assert data["action_result"]["success"] is False
        assert "customer" in data["action_result"]["message"].lower()


def test_voice_add_line_without_active_quote(
    client: TestClient, db_session: Session, mock_cognito_jwt_verify
):
    """Test add_quote_line without active quote in context."""
    headers, user_id, tenant_id = setup_test_user(client, db_session)

    with (
        patch("api.routes.voice.transcribe_audio") as mock_transcribe,
        patch("api.routes.voice.get_embedding") as mock_embedding,
        patch("api.routes.voice.parse_intent") as mock_parse_intent,
    ):
        mock_transcribe.return_value = "Add 5 breakers"
        mock_embedding.return_value = [0.1] * 1024
        mock_parse_intent.return_value = json.dumps(
            {
                "intent": "add_quote_line",
                "entities": {"quantity": 5, "item": "breakers"},
            }
        )

        files = {"audio": ("test.m4a", b"dummy audio", "audio/mp4")}
        response = client.post("/api/v1/voice/command", headers=headers, files=files)

        assert response.status_code == 200
        data = response.json()

        # Should return error about missing quote
        assert data["action_result"]["success"] is False
        assert "quote" in data["action_result"]["message"].lower()


# ==================== HANDLER-SPECIFIC TESTS ====================


def test_handler_query_job_profit(
    client: TestClient, db_session: Session, mock_cognito_jwt_verify
):
    """
    Test Handler #3: get_job_profitability
    Tests querying job profit data.
    """
    headers, user_id, tenant_id = setup_test_user(client, db_session)

    # Create test job with profitability data
    from app.models.core import Tenant, User
    from app.models.fulfillment import JobStatus

    # Get tenant and user
    tenant = db_session.get(Tenant, tenant_id)
    user = db_session.get(User, user_id)

    # Create customer
    customer = Customer(
        tenant_id=tenant_id,
        display_name="Profit Test Customer",
        type="company",
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)

    # Create site
    site = Site(
        tenant_id=tenant_id,
        customer_id=customer.id,
        name="Test Site",
    )
    db_session.add(site)
    db_session.commit()
    db_session.refresh(site)

    # Create job status
    job_status = JobStatus(
        tenant_id=tenant_id,
        code="active",
        name="Active",
        is_default=True,
    )
    db_session.add(job_status)
    db_session.commit()
    db_session.refresh(job_status)

    # Create job with cached profitability
    job = Job(
        tenant_id=tenant_id,
        customer_id=customer.id,
        site_id=site.id,
        status_id=job_status.id,
        actual_labor_cost_cents=10000,  # $100
        actual_material_cost_cents=5000,  # $50
        actual_profit_cents=3500,  # $35
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    with (
        patch("api.routes.voice.transcribe_audio") as mock_transcribe,
        patch("api.routes.voice.get_embedding") as mock_embedding,
        patch("api.routes.voice.parse_intent") as mock_parse_intent,
    ):
        mock_transcribe.return_value = "What's the profit on Profit Test Customer job"
        mock_embedding.return_value = [0.1] * 1024
        mock_parse_intent.return_value = json.dumps(
            {
                "intent": "query_job_profit",
                "entities": {"job_reference": "Profit Test Customer"},
            }
        )

        files = {"audio": ("test.m4a", b"dummy audio", "audio/mp4")}
        response = client.post("/api/v1/voice/command", headers=headers, files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["action_result"]["success"] is True
        assert data["action_result"]["data"]["profit_cents"] == 3500
        assert "$35.00" in data["action_result"]["data"]["profit_dollars"]


def test_handler_calculate_voltage_drop_placeholder(
    client: TestClient, db_session: Session, mock_cognito_jwt_verify
):
    """
    Test Handler #4: calculate_nec_voltage_drop (Task 1-E-3 full implementation)

    Updated: The placeholder was replaced with a real NEC calculation handler.
    This test now verifies the live calculation path with a complete set of entities.

    Known-good vector: 30A, 200ft, 10 AWG, 120V single-phase
        V_D = (2 × 12.9 × 30 × 200) / 10380 ≈ 14.88V → 12.4% → NOT compliant
    """
    headers, user_id, tenant_id = setup_test_user(client, db_session)

    with (
        patch("api.routes.voice.transcribe_audio") as mock_transcribe,
        patch("api.routes.voice.get_embedding") as mock_embedding,
        patch("api.routes.voice.parse_intent") as mock_parse_intent,
    ):
        mock_transcribe.return_value = (
            "Calculate voltage drop for 30 amps on 200 feet of 10 AWG"
        )
        mock_embedding.return_value = [0.1] * 1024
        mock_parse_intent.return_value = json.dumps(
            {
                "intent": "calculate_voltage_drop",
                "entities": {
                    "amperage": 30,
                    "distance_feet": 200,
                    "wire_gauge": "10 AWG",
                    "voltage": 120,
                    "phase": 1,
                },
            }
        )

        files = {"audio": ("test.m4a", b"dummy audio", "audio/mp4")}
        response = client.post("/api/v1/voice/command", headers=headers, files=files)

        assert response.status_code == 200
        data = response.json()

        # Real calculation: should succeed and return voltage drop data
        assert data["action_result"]["success"] is True
        assert "voltage_drop" in data["action_result"]["data"]
        assert "voltage_drop_pct" in data["action_result"]["data"]
        assert "is_compliant" in data["action_result"]["data"]
        # 30A, 200ft, 10 AWG at 120V → far exceeds 3% → not compliant
        assert data["action_result"]["data"]["is_compliant"] is False


def test_handler_navigate(
    client: TestClient, db_session: Session, mock_cognito_jwt_verify
):
    """
    Test Handler #5: return_navigation_command
    """
    headers, user_id, tenant_id = setup_test_user(client, db_session)

    with (
        patch("api.routes.voice.transcribe_audio") as mock_transcribe,
        patch("api.routes.voice.get_embedding") as mock_embedding,
        patch("api.routes.voice.parse_intent") as mock_parse_intent,
    ):
        mock_transcribe.return_value = "Show me active jobs"
        mock_embedding.return_value = [0.1] * 1024
        mock_parse_intent.return_value = json.dumps(
            {"intent": "navigate", "entities": {"screen": "jobs", "filter": "active"}}
        )

        files = {"audio": ("test.m4a", b"dummy audio", "audio/mp4")}
        response = client.post("/api/v1/voice/command", headers=headers, files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["action_result"]["success"] is True
        assert data["action_result"]["data"]["screen"] == "jobs"
        assert data["action_result"]["data"]["filter"] == "active"
        assert data["action_result"]["data"]["navigation_command"] is True


def test_handler_log_time_entry(
    client: TestClient, db_session: Session, mock_cognito_jwt_verify
):
    """
    Test Handler #8: log_time_entry_via_voice
    """
    headers, user_id, tenant_id = setup_test_user(client, db_session)

    # FIX: Setup required tenant user roles and status
    from app.models.auth import TenantUser, TenantUserRole, TenantUserStatus

    # Create TenantUserRole if not exists
    role = db_session.exec(
        select(TenantUserRole).where(TenantUserRole.code == "owner")
    ).first()
    if not role:
        role = TenantUserRole(
            code="owner",
            name="Owner",
            permissions={},
            is_default=True,
        )
        db_session.add(role)
        db_session.commit()

    # Create TenantUserStatus if not exists
    status = db_session.exec(
        select(TenantUserStatus)
        .where(TenantUserStatus.tenant_id == tenant_id)
        .where(TenantUserStatus.is_default == True)
    ).first()
    if not status:
        status = TenantUserStatus(
            tenant_id=tenant_id,
            code="active",
            name="Active",
            is_default=True,
        )
        db_session.add(status)
        db_session.commit()

    # Ensure TenantUser relationship exists
    tenant_user = db_session.exec(
        select(TenantUser)
        .where(TenantUser.tenant_id == tenant_id)
        .where(TenantUser.user_id == user_id)
    ).first()
    if not tenant_user:
        tenant_user = TenantUser(
            tenant_id=tenant_id,
            user_id=user_id,
            role_code=role.code,
            status_id=status.id,
            is_active=True,
        )
        db_session.add(tenant_user)
        db_session.commit()

    # Setup: Create customer, site, job status, and job
    from app.models.fulfillment import JobStatus

    customer = Customer(
        tenant_id=tenant_id,
        display_name="Time Entry Customer",
        type="company",
    )
    db_session.add(customer)
    db_session.commit()

    site = Site(
        tenant_id=tenant_id,
        customer_id=customer.id,
        name="Test Site",
    )
    db_session.add(site)
    db_session.commit()

    job_status = JobStatus(
        tenant_id=tenant_id,
        code="active",
        name="Active",
        is_default=True,
    )
    db_session.add(job_status)
    db_session.commit()

    job = Job(
        tenant_id=tenant_id,
        customer_id=customer.id,
        site_id=site.id,
        status_id=job_status.id,
    )
    db_session.add(job)
    db_session.commit()

    with (
        patch("api.routes.voice.transcribe_audio") as mock_transcribe,
        patch("api.routes.voice.get_embedding") as mock_embedding,
        patch("api.routes.voice.parse_intent") as mock_parse_intent,
    ):
        mock_transcribe.return_value = "Log 3 hours on Time Entry Customer"
        mock_embedding.return_value = [0.1] * 1024
        mock_parse_intent.return_value = json.dumps(
            {
                "intent": "log_time_entry",
                "entities": {"hours": 3, "job_reference": "Time Entry Customer"},
            }
        )

        files = {"audio": ("test.m4a", b"dummy audio", "audio/mp4")}
        response = client.post("/api/v1/voice/command", headers=headers, files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["action_result"]["success"] is True
        assert data["action_result"]["data"]["hours"] == 3

        # Verify time entry created
        time_entry = db_session.exec(
            select(JobTimeEntry).where(JobTimeEntry.job_id == job.id)
        ).first()
        assert time_entry is not None
        assert time_entry.hours == 3


def test_handler_add_expense(
    client: TestClient, db_session: Session, mock_cognito_jwt_verify
):
    """
    Test Handler #9: add_expense_via_voice
    """
    headers, user_id, tenant_id = setup_test_user(client, db_session)

    # Setup: Create job and expense category
    from app.models.fulfillment import JobStatus

    customer = Customer(
        tenant_id=tenant_id,
        display_name="Expense Customer",
        type="company",
    )
    db_session.add(customer)
    db_session.commit()

    site = Site(
        tenant_id=tenant_id,
        customer_id=customer.id,
        name="Test Site",
    )
    db_session.add(site)
    db_session.commit()

    job_status = JobStatus(
        tenant_id=tenant_id,
        code="active",
        name="Active",
        is_default=True,
    )
    db_session.add(job_status)
    db_session.commit()

    job = Job(
        tenant_id=tenant_id,
        customer_id=customer.id,
        site_id=site.id,
        status_id=job_status.id,
    )
    db_session.add(job)
    db_session.commit()

    # Use the globally seeded 'materials' category (seeded by Alembic migration).
    # Do not re-insert — job_expense_category PK is 'code' (VARCHAR) and the
    # global row already exists with tenant_id=NULL.
    expense_category = db_session.get(JobExpenseCategory, "materials")
    if expense_category is None:
        expense_category = JobExpenseCategory(
            code="materials",
            tenant_id=None,
            name="Materials & Supplies",
            is_default=True,
        )
        db_session.add(expense_category)
        db_session.commit()

    with (
        patch("api.routes.voice.transcribe_audio") as mock_transcribe,
        patch("api.routes.voice.get_embedding") as mock_embedding,
        patch("api.routes.voice.parse_intent") as mock_parse_intent,
    ):
        mock_transcribe.return_value = (
            "Add $45.99 expense for breakers from Home Depot on Expense Customer job"
        )
        mock_embedding.return_value = [0.1] * 1024
        mock_parse_intent.return_value = json.dumps(
            {
                "intent": "add_expense",
                "entities": {
                    "amount": 45.99,
                    "description": "breakers",
                    "vendor": "Home Depot",
                    "job_reference": "Expense Customer",
                },
            }
        )

        files = {"audio": ("test.m4a", b"dummy audio", "audio/mp4")}
        response = client.post("/api/v1/voice/command", headers=headers, files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["action_result"]["success"] is True
        assert data["action_result"]["data"]["cost_cents"] == 4599

        # Verify expense created
        expense = db_session.exec(
            select(JobExpense).where(JobExpense.job_id == job.id)
        ).first()
        assert expense is not None
        assert expense.cost_cents == 4599
        assert expense.description == "breakers"


def test_handler_send_quote_placeholder(
    client: TestClient, db_session: Session, mock_cognito_jwt_verify
):
    """
    Test Handler #10: send_quote_via_voice (MVP placeholder)
    """
    headers, user_id, tenant_id = setup_test_user(client, db_session)

    # Create quote first
    with (
        patch("api.routes.voice.transcribe_audio") as mock_transcribe,
        patch("api.routes.voice.get_embedding") as mock_embedding,
        patch("api.routes.voice.parse_intent") as mock_parse_intent,
    ):
        # Turn 1: Create quote
        mock_transcribe.return_value = "Create quote for Send Test Company"
        mock_embedding.return_value = [0.1] * 1024
        mock_parse_intent.return_value = json.dumps(
            {
                "intent": "create_quote",
                "entities": {"customer_name": "Send Test Company"},
            }
        )

        files1 = {"audio": ("test1.m4a", b"audio1", "audio/mp4")}
        response1 = client.post("/api/v1/voice/command", headers=headers, files=files1)
        session_id = response1.json()["session_id"]

        # Turn 2: Send quote
        mock_transcribe.return_value = "Send the quote"
        mock_parse_intent.return_value = json.dumps(
            {"intent": "send_quote", "entities": {}}
        )

        files2 = {"audio": ("test2.m4a", b"audio2", "audio/mp4")}
        form_data = {"session_id": str(session_id)}
        response2 = client.post(
            "/api/v1/voice/command", headers=headers, files=files2, data=form_data
        )

        assert response2.status_code == 200
        data = response2.json()

        # MVP placeholder should succeed with informative message
        assert data["action_result"]["success"] is True
        assert "coming soon" in data["action_result"]["message"].lower()


# ==================== TENANT ISOLATION TESTS ====================


def test_voice_action_tenant_isolation(
    client: TestClient, db_session: Session, mock_cognito_jwt_verify
):
    """
    Test that voice actions respect tenant isolation.
    User from tenant A cannot query jobs from tenant B.
    """
    import uuid

    from app.models.auth import TenantUser, TenantUserRole, TenantUserStatus
    from app.models.core import Tenant, User
    from app.models.fulfillment import JobStatus

    # Create two tenants
    tenant_a_id = uuid.uuid4()
    tenant_b_id = uuid.uuid4()

    tenant_a = Tenant(id=tenant_a_id, name="Tenant A Isolation Test", is_active=True)
    tenant_b = Tenant(id=tenant_b_id, name="Tenant B Isolation Test", is_active=True)
    db_session.add(tenant_a)
    db_session.add(tenant_b)
    db_session.commit()

    # Create user in tenant A (use unique email to avoid conflicts)
    user_a_id = uuid.uuid4()
    user_a_email = f"usera_{uuid.uuid4().hex[:8]}@test-isolation.com"
    user_a = User(
        id=user_a_id,
        email=user_a_email,
        is_active=True,
    )
    db_session.add(user_a)
    db_session.commit()

    # Create TenantUserRole and TenantUserStatus for tenant A
    role = TenantUserRole(
        code="test_role_a",
        name="Test Role A",
        permissions=["voice.use"],
        is_default=True,
    )
    db_session.add(role)
    db_session.commit()

    status_a = TenantUserStatus(
        tenant_id=tenant_a_id,
        code="active_a",
        name="Active A",
        is_default=True,
    )
    db_session.add(status_a)
    db_session.commit()

    # Create TenantUser relationship
    tenant_user_a = TenantUser(
        tenant_id=tenant_a_id,
        user_id=user_a_id,
        role_code=role.code,
        status_id=status_a.id,
        is_active=True,
    )
    db_session.add(tenant_user_a)
    db_session.commit()

    # Create customer and job in tenant B
    customer_b = Customer(
        tenant_id=tenant_b_id,
        display_name="Tenant B Customer",
        type="company",
    )
    db_session.add(customer_b)
    db_session.commit()

    site_b = Site(
        tenant_id=tenant_b_id,
        customer_id=customer_b.id,
        name="Tenant B Site",
    )
    db_session.add(site_b)
    db_session.commit()

    job_status = JobStatus(
        tenant_id=None,
        code="active_iso",
        name="Active Isolation",
        is_default=True,
    )
    db_session.add(job_status)
    db_session.commit()

    job_b = Job(
        tenant_id=tenant_b_id,
        customer_id=customer_b.id,
        site_id=site_b.id,
        status_id=job_status.id,
        actual_profit_cents=5000,
    )
    db_session.add(job_b)
    db_session.commit()

    # User A tries to query Tenant B's job
    # FIX: Mock JWT verification to return user A's email
    with patch("core.auth.verify_cognito_jwt") as mock_verify:
        mock_verify.return_value = {
            "sub": str(user_a_id),  # Use user_id as sub
            "email": user_a_email,
        }

        with (
            patch("api.routes.voice.transcribe_audio") as mock_transcribe,
            patch("api.routes.voice.get_embedding") as mock_embedding,
            patch("api.routes.voice.parse_intent") as mock_parse_intent,
        ):
            mock_transcribe.return_value = "What's the profit on Tenant B Customer"
            mock_embedding.return_value = [0.1] * 1024
            mock_parse_intent.return_value = json.dumps(
                {
                    "intent": "query_job_profit",
                    "entities": {"job_reference": "Tenant B Customer"},
                }
            )

            files = {"audio": ("test.m4a", b"dummy audio", "audio/mp4")}

            # Create proper auth headers with tenant A user
            headers = {"Authorization": f"Bearer test_token_{user_a_id}"}

            response = client.post(
                "/api/v1/voice/command", headers=headers, files=files
            )

            assert response.status_code == 200
            data = response.json()

            # Should fail to find job (tenant isolation working)
            assert data["action_result"]["success"] is False
            assert (
                "couldn't find" in data["action_result"]["message"].lower()
                or "not found" in data["action_result"]["message"].lower()
            )


# ==================== CONTEXT WINDOW TESTS ====================


def test_context_window_persistence_across_multiple_turns(
    client: TestClient, db_session: Session, mock_cognito_jwt_verify
):
    """
    Test 3-turn conversation maintaining context:
    1. Create quote
    2. Add line
    3. Add another line
    """
    headers, user_id, tenant_id = setup_test_user(client, db_session)

    # FIX: Create required QcoLineType
    from app.models.quoting import QcoLineType

    line_type = QcoLineType(
        tenant_id=tenant_id,
        code="standard",
        name="Standard Line",
        is_default=True,
    )
    db_session.add(line_type)
    db_session.commit()
    db_session.refresh(line_type)

    with (
        patch("api.routes.voice.transcribe_audio") as mock_transcribe,
        patch("api.routes.voice.get_embedding") as mock_embedding,
        patch("api.routes.voice.parse_intent") as mock_parse_intent,
    ):
        # Turn 1: Create quote
        mock_transcribe.return_value = "Create quote for Multi-Turn Test"
        mock_embedding.return_value = [0.1] * 1024
        mock_parse_intent.return_value = json.dumps(
            {"intent": "create_quote", "entities": {"customer_name": "Multi-Turn Test"}}
        )

        files1 = {"audio": ("test1.m4a", b"audio1", "audio/mp4")}
        response1 = client.post("/api/v1/voice/command", headers=headers, files=files1)
        assert response1.status_code == 200

        session_id = response1.json()["session_id"]
        quote_id = response1.json()["action_result"]["data"]["quote_id"]

        # Turn 2: Add first line
        mock_transcribe.return_value = "Add 5 breakers"
        mock_parse_intent.return_value = json.dumps(
            {
                "intent": "add_quote_line",
                "entities": {"quantity": 5, "item": "breakers"},
            }
        )

        files2 = {"audio": ("test2.m4a", b"audio2", "audio/mp4")}
        response2 = client.post(
            "/api/v1/voice/command",
            headers=headers,
            files=files2,
            data={"session_id": str(session_id)},
        )
        assert response2.status_code == 200
        assert response2.json()["action_result"]["success"] is True

        # Turn 3: Add second line
        mock_transcribe.return_value = "Add 100 feet of wire"
        mock_parse_intent.return_value = json.dumps(
            {
                "intent": "add_quote_line",
                "entities": {"quantity": 100, "unit": "feet", "item": "wire"},
            }
        )

        files3 = {"audio": ("test3.m4a", b"audio3", "audio/mp4")}
        response3 = client.post(
            "/api/v1/voice/command",
            headers=headers,
            files=files3,
            data={"session_id": str(session_id)},
        )
        assert response3.status_code == 200
        assert response3.json()["action_result"]["success"] is True

        # Verify both lines added to same quote
        quote_lines = db_session.exec(
            select(QuoteLine).where(QuoteLine.quote_id == UUID(quote_id))
        ).all()
        assert len(quote_lines) == 2
        descriptions = [line.description for line in quote_lines]
        assert "breakers" in descriptions
        assert "wire" in descriptions

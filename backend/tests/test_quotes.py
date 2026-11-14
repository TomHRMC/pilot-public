import datetime
import uuid

from fastapi.testclient import TestClient
from psycopg2.extras import DateTimeTZRange
from sqlmodel import Session, select

from app.models.billing import Currency
from app.models.crm import Contact, Customer, CustomerType, Site
from app.models.quoting import (
    PricebookItem,
    PricebookItemVersion,
    QcoLineType,
    QuoteLinkStatus,
    QuoteStatus,
)
from tests.test_phase2 import setup_test_user


def ensure_currency(db_session: Session):
    currency = db_session.exec(select(Currency).where(Currency.code == "USD")).first()
    if not currency:
        currency = Currency(code="USD", name="US Dollar", symbol="$")
        db_session.add(currency)
        db_session.flush()


def test_quote_creation(
    client: TestClient, db_session: Session, mock_cognito_jwt_verify
):
    headers, _user_id, tenant_id = setup_test_user(client, db_session)
    ensure_currency(db_session)

    # Setup Customer
    customer = Customer(
        tenant_id=tenant_id, type=CustomerType.person, display_name="Quote Customer"
    )
    db_session.add(customer)
    db_session.flush()

    # Setup Site
    site = Site(tenant_id=tenant_id, customer_id=customer.id, name="Quote Site")
    db_session.add(site)
    db_session.flush()

    # Setup Quote Status
    quote_status = QuoteStatus(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code="draft",
        name="Draft",
        is_default=True,
    )
    db_session.add(quote_status)
    db_session.commit()

    payload = {
        "customer_id": str(customer.id),
        "site_id": str(site.id),
        "currency": "USD",
    }

    response = client.post("/api/v1/quotes", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["customer_id"] == str(customer.id)
    assert data["site_id"] == str(site.id)
    assert data["status_id"] == str(quote_status.id)
    assert data["tenant_id"] == str(tenant_id)
    assert data["subtotal_cents"] == 0


def test_quote_line_snapshot_pricing(
    client: TestClient, db_session: Session, mock_cognito_jwt_verify
):
    headers, _user_id, tenant_id = setup_test_user(client, db_session)
    ensure_currency(db_session)

    # 1. Setup Quote
    customer = Customer(
        tenant_id=tenant_id, type=CustomerType.person, display_name="Line Customer"
    )
    db_session.add(customer)
    db_session.flush()

    site = Site(tenant_id=tenant_id, customer_id=customer.id, name="Line Site")
    db_session.add(site)
    db_session.flush()

    quote_status = QuoteStatus(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code="draft",
        name="Draft",
        is_default=True,
    )
    db_session.add(quote_status)
    db_session.flush()

    payload = {
        "customer_id": str(customer.id),
        "site_id": str(site.id),
    }
    response = client.post("/api/v1/quotes", json=payload, headers=headers)
    assert response.status_code == 201
    quote_id = response.json()["id"]

    # 2. Setup QcoLineType
    line_type = QcoLineType(
        id=uuid.uuid4(), tenant_id=tenant_id, code="material", name="Material"
    )
    db_session.add(line_type)
    db_session.flush()

    # 3. Setup PricebookItem and Version
    pb_item = PricebookItem(
        id=uuid.uuid4(), tenant_id=tenant_id, sku="WIRE-14-2", name="14/2 Romex"
    )
    db_session.add(pb_item)
    db_session.flush()

    valid_from = datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC)
    pb_version = PricebookItemVersion(
        tenant_id=tenant_id,
        pricebook_item_id=pb_item.id,
        default_unit_price_cents=15000,  # $150.00
        valid_period=DateTimeTZRange(lower=valid_from, upper=None, bounds="[)"),
    )
    db_session.add(pb_version)
    db_session.commit()

    # 4. Create Quote Line with PricebookItem
    line_payload = {
        "position": 1,
        "qco_line_type_id": str(line_type.id),
        "pricebook_item_id": str(pb_item.id),
        "description": "50ft 14/2 Romex",
        "quantity": 2.0,
    }

    response = client.post(
        f"/api/v1/quotes/{quote_id}/lines", json=line_payload, headers=headers
    )
    assert response.status_code == 201
    data = response.json()

    # Unit price should be copied from PricebookItemVersion (15000)
    assert data["unit_price_cents"] == 15000
    # Subtotal should be quantity (2) * unit_price (15000) = 30000
    assert data["subtotal_cents"] == 30000

    # 5. Check quote totals updated
    quote_res = client.get(f"/api/v1/quotes/{quote_id}", headers=headers)
    assert quote_res.status_code == 200
    assert quote_res.json()["subtotal_cents"] == 30000


def test_quote_versioning(
    client: TestClient, db_session: Session, mock_cognito_jwt_verify
):
    headers, _user_id, tenant_id = setup_test_user(client, db_session)
    ensure_currency(db_session)

    # 1. Setup Quote
    customer = Customer(
        tenant_id=tenant_id, type=CustomerType.person, display_name="Version Customer"
    )
    db_session.add(customer)
    db_session.flush()

    site = Site(tenant_id=tenant_id, customer_id=customer.id, name="Version Site")
    db_session.add(site)
    db_session.flush()

    quote_status = QuoteStatus(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code="draft",
        name="Draft",
        is_default=True,
    )
    db_session.add(quote_status)
    db_session.flush()

    payload = {
        "customer_id": str(customer.id),
        "site_id": str(site.id),
    }
    response = client.post("/api/v1/quotes", json=payload, headers=headers)
    assert response.status_code == 201
    quote_id = response.json()["id"]

    # 2. Add Line
    line_type = QcoLineType(
        id=uuid.uuid4(), tenant_id=tenant_id, code="service", name="Service"
    )
    db_session.add(line_type)
    db_session.commit()

    line_payload = {
        "position": 1,
        "qco_line_type_id": str(line_type.id),
        "description": "Consultation",
        "quantity": 1.0,
        "unit_price_cents": 5000,
    }
    response = client.post(
        f"/api/v1/quotes/{quote_id}/lines", json=line_payload, headers=headers
    )
    assert response.status_code == 201

    # 3. Create Version
    response = client.post(f"/api/v1/quotes/{quote_id}/versions", headers=headers)
    assert response.status_code == 201
    data = response.json()

    # PLP-FIX-3: quote creation now auto-creates v1, so the explicit version is v2.
    assert data["version_no"] == 2
    assert data["quote_id"] == quote_id
    snapshot = data["snapshot"]
    assert snapshot["quote"]["id"] == quote_id
    assert len(snapshot["lines"]) == 1
    assert snapshot["lines"][0]["description"] == "Consultation"


def test_quote_public_link(
    client: TestClient, db_session: Session, mock_cognito_jwt_verify
):
    headers, _user_id, tenant_id = setup_test_user(client, db_session)
    ensure_currency(db_session)

    # Setup Quote & Version
    customer = Customer(
        tenant_id=tenant_id, type=CustomerType.person, display_name="Link Customer"
    )
    db_session.add(customer)
    db_session.flush()

    site = Site(tenant_id=tenant_id, customer_id=customer.id, name="Link Site")
    db_session.add(site)
    db_session.flush()

    quote_status = QuoteStatus(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code="draft",
        name="Draft",
        is_default=True,
    )
    db_session.add(quote_status)
    db_session.flush()

    quote_res = client.post(
        "/api/v1/quotes",
        json={"customer_id": str(customer.id), "site_id": str(site.id)},
        headers=headers,
    )
    quote_id = quote_res.json()["id"]

    version_res = client.post(f"/api/v1/quotes/{quote_id}/versions", headers=headers)
    version_id = version_res.json()["id"]

    # Setup Contact
    contact = Contact(tenant_id=tenant_id, customer_id=customer.id, first_name="Link")
    db_session.add(contact)
    db_session.flush()

    # Setup QuoteLinkStatus
    link_status = QuoteLinkStatus(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code="active",
        name="Active",
        is_default=True,
    )
    db_session.add(link_status)
    db_session.commit()

    # Create Public Link
    payload = {
        "contact_id": str(contact.id),
        "status_id": str(link_status.id),
    }

    response = client.post(
        f"/api/v1/quotes/{quote_id}/versions/{version_id}/public-link",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()

    assert "url" in data
    assert data["url"].startswith("https://frontend-domain.com/quote/")
    assert data["contact_id"] == str(contact.id)

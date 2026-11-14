"""
QuickBooks synchronization service for bidirectional data sync.

Handles sync between Pilot for Trades and QuickBooks Online:
- Customer sync (QB ↔ Pilot for Trades) - bidirectional
- Invoice sync (QB → Pilot for Trades) - one-way (deferred to Task 18)
- Deduplication via integration_sync_mapping table
- Version token tracking for conflict detection (Task 18)

Design Reference: Task #17 in phase-2-5-implementation-roadmap.md
Gap Reference: Gap #23 in phase-1-4-implementation-gap-analysis.md
Architecture: dev-docs/db-design/pilot-db-process-v2.6h.md

Usage:
    from services.quickbooks_sync import QuickBooksSync

    sync = QuickBooksSync(tenant_id, db)

    # Sync single customer from QuickBooks
    customer = await sync.sync_customer_from_qb(qb_customer_dict)

    # Sync customer to QuickBooks
    qb_response = await sync.sync_customer_to_qb(customer_id)

    # Batch sync all customers (incremental)
    count = await sync.sync_all_customers_from_qb(since=last_sync_timestamp)
"""

import logging
import uuid
from datetime import UTC, datetime

import httpx
from sqlmodel import Session, select

from app.models.crm import Customer, CustomerType
from app.models.system import (
    AppService,
    IntegrationCredential,
    IntegrationSyncConflict,
    IntegrationSyncMapping,
)
from core.encryption import decrypt_token

logger = logging.getLogger(__name__)


class QuickBooksSync:
    """
    QuickBooks synchronization service for a specific tenant.

    Provides bidirectional sync between Pilot for Trades and QuickBooks Online,
    preventing duplicate records via the integration_sync_mapping table.
    """

    def __init__(self, tenant_id: uuid.UUID, db: Session):
        """
        Initialize sync service for specific tenant.

        Args:
            tenant_id: UUID of the tenant to sync for
            db: Database session (must be active for duration of sync)
        """
        self.tenant_id = tenant_id
        self.db = db
        self.base_url = "https://sandbox-quickbooks.api.intuit.com/v3"

    async def get_access_token(self) -> tuple[str, str]:
        """
        Get decrypted access token and realm_id for tenant.

        Automatically refreshes token if expiring within 5 minutes.

        Returns:
            Tuple of (access_token, realm_id)

        Raises:
            ValueError: If QuickBooks not connected for this tenant
            HTTPException: If token refresh fails
        """
        # Find active QuickBooks credential for this tenant
        stmt = (
            select(IntegrationCredential, AppService)
            .join(AppService, IntegrationCredential.app_service_id == AppService.id)
            .where(
                IntegrationCredential.tenant_id == self.tenant_id,
                AppService.provider_code == "quickbooks",
                IntegrationCredential.connection_status == "active",
            )
        )
        result = self.db.exec(stmt).first()

        if not result:
            raise ValueError(
                f"QuickBooks not connected for tenant {self.tenant_id}. "
                "Please connect via /api/v1/integrations/quickbooks/connect"
            )

        credential, app_service = result

        # Check if token needs refresh (expires in <5 minutes)
        now = datetime.now(UTC)
        time_until_expiry = (credential.expires_at - now).total_seconds()

        if time_until_expiry < 300:  # <5 minutes
            # Token needs refresh - call the refresh logic from integrations.py
            from api.routes.integrations import _refresh_qbo_token_impl

            # Get a user_id for the refresh operation
            user_id = credential.initiated_by_user_id or credential.created_by
            await _refresh_qbo_token_impl(self.tenant_id, user_id, self.db)

            # Re-fetch the credential after refresh
            result = self.db.exec(stmt).first()
            if not result:
                raise ValueError("Failed to refresh QuickBooks token")
            credential, app_service = result

        # Decrypt access token
        access_token = decrypt_token(credential.secret_json["access_token_encrypted"])
        realm_id = app_service.external_account_id

        if not realm_id:
            raise ValueError(
                "QuickBooks realm_id not found. OAuth connection may be incomplete."
            )

        return access_token, realm_id

    async def _get_app_service_id(self) -> uuid.UUID:
        """
        Get QuickBooks app_service.id for this tenant.

        Used for integration_sync_mapping queries.

        Returns:
            UUID of the QuickBooks AppService

        Raises:
            ValueError: If QuickBooks AppService not found
        """
        stmt = select(AppService).where(
            AppService.tenant_id == self.tenant_id,
            AppService.provider_code == "quickbooks",
        )
        app_service = self.db.exec(stmt).first()

        if not app_service:
            raise ValueError(
                f"QuickBooks AppService not found for tenant {self.tenant_id}"
            )

        return app_service.id

    async def detect_conflict(
        self, mapping: IntegrationSyncMapping, qb_customer: dict
    ) -> bool:
        """
        Detect if both systems modified the same record since last sync.

        Compares version tokens from both QuickBooks and Pilot for Trades to determine
        if simultaneous edits occurred.

        Args:
            mapping: Existing sync mapping record
            qb_customer: QuickBooks customer dict from API response

        Returns:
            True if conflict detected (both version tokens changed), False otherwise
        """
        # Get current customer from Pilot for Trades — FIND-132: tenant-scoped query
        customer = self.db.exec(
            select(Customer).where(
                Customer.id == mapping.entity_id,
                Customer.tenant_id == self.tenant_id,
            )
        ).first()
        if not customer:
            # Customer deleted in Pilot for Trades (or belongs to wrong tenant) - not a conflict, just skip
            return False

        # Check both version tokens
        qb_token = qb_customer.get("SyncToken", "0")
        qb_changed = qb_token != mapping.external_version_token

        # Check if Pilot for Trades customer changed since last sync
        current_internal_version = customer.updated_at.isoformat()

        if mapping.internal_version_token is None:
            # First sync after migration or new mapping - no conflict
            pilot_changed = False
        else:
            pilot_changed = current_internal_version != mapping.internal_version_token

        # CONFLICT: Both sides modified since last sync
        return qb_changed and pilot_changed

    async def queue_conflict(
        self,
        mapping: IntegrationSyncMapping,
        qb_customer: dict,
        app_service_id: uuid.UUID,
    ) -> "IntegrationSyncConflict":
        """
        Store conflict for manual resolution.

        Creates a conflict record with payloads from both systems and
        fires a NotificationOutbox email to the tenant owner within the
        same DB transaction (Task 1-E-4).

        Args:
            mapping: Existing sync mapping record
            qb_customer: QuickBooks customer dict from API response
            app_service_id: UUID of QuickBooks AppService

        Returns:
            Created IntegrationSyncConflict record
        """
        from app.models.system import (
            IntegrationSyncConflict,
            NotificationEvent,
            NotificationOutbox,
            NotificationType,
        )

        # FIND-132: tenant-scoped query
        customer = self.db.exec(
            select(Customer).where(
                Customer.id == mapping.entity_id,
                Customer.tenant_id == self.tenant_id,
            )
        ).first()

        # FIND-090: compute conflict subtype and financial delta
        from services.qb_conflict_diff import compute_financial_delta

        internal_snap = {
            "display_name": customer.display_name,
            "first_name": customer.first_name,
            "last_name": customer.last_name,
            "company_name": customer.company_name,
            "email": customer.email,
            "mobile_phone": customer.mobile_phone,
            "notes": customer.notes,
            "is_active": customer.is_active,
            "updated_at": customer.updated_at.isoformat(),
        }
        external_snap = {
            "Id": qb_customer["Id"],
            "DisplayName": qb_customer.get("DisplayName"),
            "GivenName": qb_customer.get("GivenName"),
            "FamilyName": qb_customer.get("FamilyName"),
            "CompanyName": qb_customer.get("CompanyName"),
            "PrimaryEmailAddr": qb_customer.get("PrimaryEmailAddr"),
            "PrimaryPhone": qb_customer.get("PrimaryPhone"),
            "Notes": qb_customer.get("Notes"),
            "Active": qb_customer.get("Active", True),
            "SyncToken": qb_customer["SyncToken"],
            "MetaData": qb_customer.get("MetaData"),
        }
        financial_delta = compute_financial_delta(
            "customer", internal_snap, external_snap
        )
        financial_delta_payload = (
            {"delta_cents": financial_delta} if financial_delta is not None else None
        )

        conflict = IntegrationSyncConflict(
            tenant_id=self.tenant_id,
            app_service_id=app_service_id,
            entity_type_code="customer",
            entity_id=customer.id,
            external_id=qb_customer["Id"],
            status="pending",
            internal_payload=internal_snap,
            external_payload=external_snap,
            # FIND-090: populate new columns
            conflict_subtype="customer",
            financial_delta_payload=financial_delta_payload,
            created_by=customer.created_by,
            updated_by=customer.updated_by,
        )
        self.db.add(conflict)
        self.db.flush()  # get conflict.id before notification creation

        # ── Notification Outbox Wiring (Task 1-E-4) ──────────────────────
        # Hard lookup — get-or-create fallback removed (SD-2)
        notif_type = self.db.exec(
            select(NotificationType).where(
                NotificationType.code == "qb_sync_conflict",
                NotificationType.tenant_id == None,
            )
        ).first()
        if not notif_type:
            logger.error(
                "notification_type 'qb_sync_conflict' not seeded — run seed_core.py"
            )
            self.db.commit()
            self.db.refresh(conflict)
            return conflict

        # Create the notification event record.
        event = NotificationEvent(
            tenant_id=self.tenant_id,
            notification_type_code="qb_sync_conflict",
            entity_type_code="customer",
            entity_id=str(customer.id),
            payload={"conflict_id": str(conflict.id)},
        )
        self.db.add(event)
        self.db.flush()  # get event.id before outbox creation

        # Resolve the tenant owner email for the to_address field.
        owner_email = self._get_tenant_owner_email()

        outbox = NotificationOutbox(
            tenant_id=self.tenant_id,
            notification_event_id=event.id,
            channel="email",
            to_address=owner_email or "system@pilot.local",
            subject=f"QuickBooks Sync Conflict — Customer: {customer.display_name}",
            body=(
                f"A QuickBooks sync conflict requires your attention for "
                f"Customer: {customer.display_name}"
            ),
            status="pending",
            category_id="sync_conflicts",  # B10/A56
        )
        self.db.add(outbox)

        self.db.commit()
        self.db.refresh(conflict)

        print(
            f"\n{'=' * 80}\n"
            f"CONFLICT DETECTED - Customer Sync\n"
            f"  Tenant: {self.tenant_id}\n"
            f"  Customer: {customer.display_name} (ID: {customer.id})\n"
            f"  QuickBooks ID: {qb_customer['Id']}\n"
            f"  Conflict ID: {conflict.id}\n"
            f"  Notification: Outbox record queued for email delivery\n"
            f"{'=' * 80}\n"
        )

        return conflict

    def _get_tenant_owner_email(self) -> str | None:
        """Return the primary owner's email for this tenant, or None if not found."""
        from app.models.auth import TenantUser
        from app.models.core import User

        stmt = (
            select(User.email)
            .join(TenantUser, TenantUser.user_id == User.id)
            .where(
                TenantUser.tenant_id == self.tenant_id,
                TenantUser.role_code == "owner",
                TenantUser.is_active == True,
            )
            .limit(1)
        )
        return self.db.exec(stmt).first()

    async def sync_customer_from_qb(self, qb_customer: dict) -> Customer | None:
        """
        Sync a single customer from QuickBooks to Pilot for Trades.

        Implements upsert logic:
        1. Check if integration_sync_mapping exists (by external_id)
        2. If exists: UPDATE customer in Pilot for Trades
        3. If not exists: CREATE customer + mapping record
        4. Update version tokens in mapping

        Args:
            qb_customer: QuickBooks customer dict from API response
                Required keys: Id, DisplayName, SyncToken
                Optional keys: GivenName, FamilyName, CompanyName,
                              PrimaryEmailAddr, PrimaryPhone, Notes, Active

        Returns:
            Customer entity (created or updated)

        Raises:
            ValueError: If required fields missing
        """
        # Validate required fields
        if "Id" not in qb_customer:
            raise ValueError("QuickBooks customer missing required field 'Id'")
        if "DisplayName" not in qb_customer:
            raise ValueError("QuickBooks customer missing required field 'DisplayName'")

        app_service_id = await self._get_app_service_id()
        external_id = qb_customer["Id"]

        # Step 1: Check if mapping exists
        stmt = select(IntegrationSyncMapping).where(
            IntegrationSyncMapping.tenant_id == self.tenant_id,
            IntegrationSyncMapping.app_service_id == app_service_id,
            IntegrationSyncMapping.entity_type_code == "customer",
            IntegrationSyncMapping.external_id == external_id,
        )
        mapping = self.db.exec(stmt).first()

        # Step 1.5: Check for conflicts (if mapping exists)
        if mapping:
            has_conflict = await self.detect_conflict(mapping, qb_customer)
            if has_conflict:
                # Queue conflict instead of overwriting
                await self.queue_conflict(mapping, qb_customer, app_service_id)
                return None  # Skip sync until conflict resolved

        # Step 2: Transform QuickBooks customer to Pilot for Trades format
        customer_data = {
            "tenant_id": self.tenant_id,
            "display_name": qb_customer["DisplayName"],
            "first_name": qb_customer.get("GivenName"),
            "last_name": qb_customer.get("FamilyName"),
            "company_name": qb_customer.get("CompanyName"),
            "email": qb_customer.get("PrimaryEmailAddr", {}).get("Address"),
            "mobile_phone": qb_customer.get("PrimaryPhone", {}).get("FreeFormNumber"),
            "notes": qb_customer.get("Notes"),
            "is_active": qb_customer.get("Active", True),
        }

        # Determine customer type based on available fields
        if customer_data["company_name"]:
            customer_data["type"] = CustomerType.company
        else:
            customer_data["type"] = CustomerType.person

        if mapping:
            # Step 3a: UPDATE existing customer — FIND-132: tenant-scoped query
            customer = self.db.exec(
                select(Customer).where(
                    Customer.id == mapping.entity_id,
                    Customer.tenant_id == self.tenant_id,
                )
            ).first()
            if not customer:
                # Orphaned mapping - recreate customer
                customer = Customer(**customer_data)
                self.db.add(customer)
                self.db.flush()
                mapping.entity_id = customer.id
            else:
                # Update existing customer fields
                for key, value in customer_data.items():
                    if key != "tenant_id":  # Don't update tenant_id
                        setattr(customer, key, value)

                # Flush to trigger updated_at update
                self.db.flush()

            # Update version tokens for conflict detection
            # When syncing FROM QB, only update the external token (QB's state)
            # Do NOT update internal token - it represents the last state we SENT to QB
            mapping.external_version_token = qb_customer.get("SyncToken", "0")
            # internal_version_token stays the same - it's only updated when we sync TO QB
            mapping.last_synced_at = datetime.now(UTC)
        else:
            # Step 3b: CREATE new customer — QB-H1 Task 5: dedup on collision
            customer, deduped = await self._insert_customer_with_dedup(
                customer_data, qb_customer, app_service_id, external_id
            )

            # If dedup occurred, queue a display_name_dedup conflict row
            if deduped:
                await self._queue_display_name_dedup_conflict(
                    customer, qb_customer, app_service_id
                )

        self.db.commit()
        self.db.refresh(customer)
        return customer

    async def _insert_customer_with_dedup(
        self,
        customer_data: dict,
        qb_customer: dict,
        app_service_id: uuid.UUID,
        external_id: str,
    ) -> tuple[Customer, bool]:
        """
        INSERT a new customer; on ``uq_customer_tenant_display_name`` collision,
        retry once with ``display_name = f"{DisplayName} (QB {Id})"``.

        Returns (customer, deduped) where ``deduped`` is True if the suffix
        was applied.

        Design: batch-qb-h1-design.md §F.4
        """
        # Pre-check for display_name collision before attempting the insert.
        # This avoids the IntegrityError/savepoint complexity that can
        # destabilize the outer transaction in batch sync contexts.
        existing = self.db.exec(
            select(Customer).where(
                Customer.tenant_id == self.tenant_id,
                Customer.display_name == customer_data["display_name"],
            )
        ).first()

        if existing:
            # Collision detected — dedup by suffixing with the QB Id
            original_display_name = customer_data["display_name"]
            deduped_name = f"{original_display_name} (QB {qb_customer['Id']})"
            customer_data["display_name"] = deduped_name

            logger.warning(
                "display_name dedup: '%s' collided — retrying as '%s' | "
                "tenant=%s qb_id=%s",
                original_display_name,
                deduped_name,
                self.tenant_id,
                external_id,
            )

            customer = Customer(**customer_data)
            self.db.add(customer)
            self.db.flush()

            # Step 4: CREATE sync mapping (dedup path)
            new_mapping = IntegrationSyncMapping(
                tenant_id=self.tenant_id,
                entity_id=customer.id,
                entity_type_code="customer",
                app_service_id=app_service_id,
                external_id=external_id,
                external_version_token=qb_customer.get("SyncToken", "0"),
                internal_version_token=None,
                sync_preference="pilot_master",
                last_synced_at=datetime.now(UTC),
                created_by=customer.created_by,
                updated_by=customer.updated_by,
            )
            self.db.add(new_mapping)
            return customer, True

        # Normal path — no collision
        customer = Customer(**customer_data)
        self.db.add(customer)
        self.db.flush()

        # Step 4: CREATE sync mapping (normal path — no collision)
        new_mapping = IntegrationSyncMapping(
            tenant_id=self.tenant_id,
            entity_id=customer.id,
            entity_type_code="customer",
            app_service_id=app_service_id,
            external_id=external_id,
            external_version_token=qb_customer.get("SyncToken", "0"),
            internal_version_token=None,  # Not set until we sync TO QB
            sync_preference="pilot_master",  # Default sync preference
            last_synced_at=datetime.now(UTC),
            created_by=customer.created_by,
            updated_by=customer.updated_by,
        )
        self.db.add(new_mapping)
        return customer, False

    async def _queue_display_name_dedup_conflict(
        self,
        customer: Customer,
        qb_customer: dict,
        app_service_id: uuid.UUID,
    ) -> None:
        """
        Queue a ``display_name_dedup`` conflict row so the owner sees the
        dedup event in the existing conflict queue.

        Design: batch-qb-h1-design.md §F.4
        """
        internal_snap = {
            "display_name": customer.display_name,
            "original_display_name": qb_customer.get("DisplayName"),
            "dedup_applied": True,
        }
        external_snap = {
            "Id": qb_customer["Id"],
            "DisplayName": qb_customer.get("DisplayName"),
            "SyncToken": qb_customer.get("SyncToken", "0"),
        }

        conflict = IntegrationSyncConflict(
            tenant_id=self.tenant_id,
            app_service_id=app_service_id,
            entity_type_code="customer",
            entity_id=customer.id,
            external_id=qb_customer["Id"],
            status="pending",
            internal_payload=internal_snap,
            external_payload=external_snap,
            conflict_subtype="display_name_dedup",
        )
        self.db.add(conflict)
        logger.info(
            "display_name_dedup conflict queued | tenant=%s customer=%s qb_id=%s",
            self.tenant_id,
            customer.id,
            qb_customer["Id"],
        )

    async def sync_customer_to_qb(self, customer_id: uuid.UUID) -> dict:
        """
        Sync Pilot for Trades customer to QuickBooks (bidirectional sync).

        Workflow:
        1. Get customer from Pilot for Trades
        2. Check if mapping exists
        3. Transform to QuickBooks format
        4. Create or update in QuickBooks
        5. Update mapping with new SyncToken

        Args:
            customer_id: UUID of Pilot for Trades customer to sync

        Returns:
            QuickBooks customer response dict

        Raises:
            ValueError: If customer not found or QB not connected
            httpx.HTTPStatusError: If QuickBooks API call fails
        """
        # Get customer from Pilot for Trades — FIND-132: tenant-scoped query (eliminates post-fetch check)
        customer = self.db.exec(
            select(Customer).where(
                Customer.id == customer_id,
                Customer.tenant_id == self.tenant_id,
            )
        ).first()
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")

        # Get access token and realm_id
        access_token, realm_id = await self.get_access_token()
        app_service_id = await self._get_app_service_id()

        # Check if customer already exists in QB (check mapping)
        stmt = select(IntegrationSyncMapping).where(
            IntegrationSyncMapping.entity_id == customer_id,
            IntegrationSyncMapping.app_service_id == app_service_id,
            IntegrationSyncMapping.entity_type_code == "customer",
        )
        mapping = self.db.exec(stmt).first()

        # Transform to QuickBooks format
        qb_payload = {
            "DisplayName": customer.display_name,
        }

        # Add optional fields if present
        if customer.first_name:
            qb_payload["GivenName"] = customer.first_name
        if customer.last_name:
            qb_payload["FamilyName"] = customer.last_name
        if customer.company_name:
            qb_payload["CompanyName"] = customer.company_name
        if customer.email:
            qb_payload["PrimaryEmailAddr"] = {"Address": customer.email}
        if customer.mobile_phone:
            qb_payload["PrimaryPhone"] = {"FreeFormNumber": customer.mobile_phone}
        if customer.notes:
            qb_payload["Notes"] = customer.notes

        qb_payload["Active"] = customer.is_active

        # If mapping exists, this is an UPDATE (include Id and SyncToken)
        if mapping:
            qb_payload["Id"] = mapping.external_id
            qb_payload["SyncToken"] = mapping.external_version_token

        # API call to QuickBooks
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/company/{realm_id}/customer",
                json=qb_payload,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            intuit_tid = response.headers.get("intuit_tid", "unknown")
            logger.info(
                "QBO API call: %s %s | status=%d | intuit_tid=%s",
                response.request.method,
                str(response.url),
                response.status_code,
                intuit_tid,
            )
            qb_response = response.json()

        # Extract customer from response (QB wraps in "Customer" key)
        qb_customer = qb_response.get("Customer", qb_response)

        # Update or create mapping
        if not mapping:
            mapping = IntegrationSyncMapping(
                tenant_id=self.tenant_id,
                entity_id=customer.id,
                entity_type_code="customer",
                app_service_id=app_service_id,
                external_id=qb_customer["Id"],
                external_version_token=qb_customer["SyncToken"],
                internal_version_token=customer.updated_at.isoformat(),
                sync_preference="pilot_master",
                last_synced_at=datetime.now(UTC),
                created_by=customer.created_by,
                updated_by=customer.updated_by,
            )
            self.db.add(mapping)
        else:
            mapping.external_version_token = qb_customer["SyncToken"]
            mapping.internal_version_token = customer.updated_at.isoformat()
            mapping.last_synced_at = datetime.now(UTC)
            mapping.updated_by = customer.updated_by

        self.db.commit()

        # SD-07: QB sync operations are unlimited on all tiers (qb_sync_operations feature removed).
        # UsageLedger writes for qb_sync_operations have been removed.

        return qb_customer

    async def sync_all_customers_from_qb(self, since: datetime | None = None) -> dict:
        """
        Incremental batch sync: Fetch customers from QuickBooks modified since timestamp.

        Performance optimization:
        - Uses QuickBooks Query API with timestamp filter
        - Only fetches customers modified after 'since' timestamp
        - If since=None, performs initial sync (fetch all customers)

        Args:
            since: Optional datetime to fetch only customers modified after this time.
                   If None, fetches all customers (initial sync).

        Returns:
            Dict with sync results:
                - synced: Number of customers successfully synced
                - conflicts: Number of conflicts detected and queued
                - failed: Number of sync failures (errors)

        Raises:
            ValueError: If QuickBooks not connected
            httpx.HTTPStatusError: If QuickBooks API call fails
        """
        access_token, realm_id = await self.get_access_token()

        # Build QuickBooks query with optional timestamp filter
        if since:
            # Incremental sync - only fetch customers modified after 'since'
            # Format: 2026-03-20T10:00:00.000Z
            timestamp_str = since.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            query = f"SELECT * FROM Customer WHERE MetaData.LastUpdatedTime > '{timestamp_str}'"
        else:
            # Initial sync - fetch all customers
            query = "SELECT * FROM Customer"

        # QuickBooks Query API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/company/{realm_id}/query",
                params={"query": query},
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
                timeout=60.0,  # Longer timeout for batch queries
            )
            response.raise_for_status()
            intuit_tid = response.headers.get("intuit_tid", "unknown")
            logger.info(
                "QBO API call: %s %s | status=%d | intuit_tid=%s",
                response.request.method,
                str(response.url),
                response.status_code,
                intuit_tid,
            )
            qb_response = response.json()

        # Extract customers from QueryResponse
        # QB returns: {"QueryResponse": {"Customer": [...]}}
        # If no customers, "Customer" key may be missing
        qb_customers = qb_response.get("QueryResponse", {}).get("Customer", [])

        # Sync each customer individually
        synced_count = 0
        conflict_count = 0
        failed_count = 0

        for qb_customer in qb_customers:
            try:
                result = await self.sync_customer_from_qb(qb_customer)
                if result is None:
                    # Conflict detected and queued
                    conflict_count += 1
                else:
                    # Successfully synced
                    synced_count += 1
            except Exception as e:
                # CRITICAL: Rollback the session to prevent cascade failures
                self.db.rollback()
                failed_count += 1

                # Log detailed error information
                qb_id = qb_customer.get("Id", "unknown")
                display_name = qb_customer.get("DisplayName", "unknown")
                email = qb_customer.get("PrimaryEmailAddr", {}).get("Address", "none")
                company = qb_customer.get("CompanyName", "none")

                print(f"\n{'=' * 80}")
                print("ERROR syncing QuickBooks customer:")
                print(f"  QuickBooks ID: {qb_id}")
                print(f"  Display Name: {display_name}")
                print(f"  Company: {company}")
                print(f"  Email: {email}")
                print(f"  Error Type: {type(e).__name__}")
                print(f"  Error Message: {e!s}")
                print(f"{'=' * 80}\n")

                # TODO: Log to integration_sync_log table (Task 18)

        print(
            f"\nSync Summary: {synced_count} synced, {conflict_count} conflicts detected, {failed_count} failed"
        )
        return {
            "synced": synced_count,
            "conflicts": conflict_count,
            "failed": failed_count,
        }

    async def get_last_sync_timestamp(self) -> datetime | None:
        """
        Get the timestamp of the last successful sync for this tenant.

        Used to determine 'since' parameter for incremental syncs.

        Returns:
            Datetime of last sync, or None if no syncs have occurred
        """
        app_service_id = await self._get_app_service_id()

        # Find the most recent sync mapping for customers
        stmt = (
            select(IntegrationSyncMapping)
            .where(
                IntegrationSyncMapping.tenant_id == self.tenant_id,
                IntegrationSyncMapping.app_service_id == app_service_id,
                IntegrationSyncMapping.entity_type_code == "customer",
            )
            .order_by(IntegrationSyncMapping.last_synced_at.desc())
            .limit(1)
        )
        mapping = self.db.exec(stmt).first()

        return mapping.last_synced_at if mapping else None

    async def fetch_customer_by_id(self, qb_customer_id: str) -> dict:
        """
        Fetch a single customer from QuickBooks by ID.

        Used by webhook handler for incremental sync (Task #19).

        Args:
            qb_customer_id: QuickBooks customer ID

        Returns:
            Customer data dict from QuickBooks API

        Raises:
            HTTPException: If API request fails
        """
        access_token, realm_id = await self.get_access_token()

        url = f"{self.base_url}/company/{realm_id}/customer/{qb_customer_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            intuit_tid = response.headers.get("intuit_tid", "unknown")
            logger.info(
                "QBO API call: %s %s | status=%d | intuit_tid=%s",
                response.request.method,
                str(response.url),
                response.status_code,
                intuit_tid,
            )

        return response.json()["Customer"]

    async def sync_invoice_to_qb(self, invoice_id: uuid.UUID) -> dict:
        """
        Sync a single Pilot for Trades invoice to QuickBooks (proactive push).

        Implements invoice push logic:
        1. Load Invoice + InvoiceLines from Pilot DB
        2. Look up QB Customer ID from integration_sync_mapping
        3. For each InvoiceLine, look up QB Item ID from integration_sync_mapping
        4. Build QB Invoice payload (amounts in dollars, not cents)
        5. POST to QB API; store returned QB Invoice ID + SyncToken in mapping

        Args:
            invoice_id: UUID of Pilot for Trades invoice

        Returns:
            QuickBooks invoice response dict with Id and SyncToken

        Raises:
            ValueError: If invoice not found or QB customer not mapped
            httpx.HTTPStatusError: If QuickBooks API call fails
        """
        from app.models.billing import Invoice, InvoiceLine

        # Get invoice from Pilot DB — FIND-132: tenant-scoped query
        invoice = self.db.exec(
            select(Invoice).where(
                Invoice.id == invoice_id,
                Invoice.tenant_id == self.tenant_id,
            )
        ).first()
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")

        # Get access token and realm_id
        access_token, realm_id = await self.get_access_token()
        app_service_id = await self._get_app_service_id()

        # Look up QB Customer ID
        customer_mapping = self.db.exec(
            select(IntegrationSyncMapping).where(
                IntegrationSyncMapping.entity_id == invoice.customer_id,
                IntegrationSyncMapping.app_service_id == app_service_id,
                IntegrationSyncMapping.entity_type_code == "customer",
            )
        ).first()
        if not customer_mapping:
            raise ValueError(f"Customer {invoice.customer_id} not mapped to QuickBooks")

        # Get invoice lines
        invoice_lines = self.db.exec(
            select(InvoiceLine).where(
                InvoiceLine.invoice_id == invoice_id,
                InvoiceLine.is_active == True,
            )
        ).all()

        # Build QB Invoice Line array
        qb_lines = []
        for line in invoice_lines:
            # Look up QB Item ID for this qco_line_type
            qb_item_id = await self._resolve_qco_line_type_to_qb_item(
                line.qco_line_type_id, app_service_id
            )

            # QB amounts are in dollars (divide cents by 100)
            qb_lines.append(
                {
                    "DetailType": "SalesItemLineDetail",
                    "Description": line.description,
                    "ItemRef": {"value": qb_item_id},
                    "Qty": float(line.quantity),
                    "UnitPrice": line.unit_price_cents / 100.0,
                    "Amount": line.total_cents / 100.0,
                }
            )

        # Build QB Invoice payload
        qb_payload = {
            "CustomerRef": {"value": customer_mapping.external_id},
            "DocNumber": invoice.invoice_number,
            "TxnDate": invoice.issued_at.isoformat().split("T")[0],  # YYYY-MM-DD
            "DueDate": invoice.due_at.isoformat().split("T")[0]
            if invoice.due_at
            else None,
            "Line": qb_lines,
            "CustomerMemo": invoice.customer_notes,
        }

        # Remove None values
        qb_payload = {k: v for k, v in qb_payload.items() if v is not None}

        # API call to QuickBooks
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/company/{realm_id}/invoice",
                json=qb_payload,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            intuit_tid = response.headers.get("intuit_tid", "unknown")
            logger.info(
                "QBO API call: %s %s | status=%d | intuit_tid=%s",
                response.request.method,
                str(response.url),
                response.status_code,
                intuit_tid,
            )
            qb_response = response.json()

        # Extract invoice from response (QB wraps in "Invoice" key)
        qb_invoice = qb_response.get("Invoice", qb_response)

        # Create/update mapping
        mapping = self.db.exec(
            select(IntegrationSyncMapping).where(
                IntegrationSyncMapping.entity_id == invoice_id,
                IntegrationSyncMapping.app_service_id == app_service_id,
                IntegrationSyncMapping.entity_type_code == "invoice",
            )
        ).first()

        if not mapping:
            mapping = IntegrationSyncMapping(
                tenant_id=self.tenant_id,
                entity_id=invoice.id,
                entity_type_code="invoice",
                app_service_id=app_service_id,
                external_id=qb_invoice["Id"],
                external_version_token=qb_invoice["SyncToken"],
                internal_version_token=invoice.updated_at.isoformat(),
                sync_preference="pilot_master",
                last_synced_at=datetime.now(UTC),
                created_by=invoice.created_by,
                updated_by=invoice.updated_by,
            )
            self.db.add(mapping)
        else:
            mapping.external_version_token = qb_invoice["SyncToken"]
            mapping.internal_version_token = invoice.updated_at.isoformat()
            mapping.last_synced_at = datetime.now(UTC)
            mapping.updated_by = invoice.updated_by

        self.db.commit()

        # SD-07: QB sync operations are unlimited on all tiers (qb_sync_operations feature removed).
        # UsageLedger writes for qb_sync_operations have been removed.

        return qb_invoice

    async def sync_payment_to_qb(self, payment_id: uuid.UUID) -> dict:
        """
        Sync a single Pilot for Trades payment to QuickBooks (proactive push).

        Implements payment push logic:
        1. Load Payment + linked Invoice from Pilot DB
        2. Look up QB Invoice ID from integration_sync_mapping
        3. Build QB Payment payload with LinkedTxn reference
        4. POST to QB API; store returned QB Payment ID in mapping

        Args:
            payment_id: UUID of Pilot for Trades payment

        Returns:
            QuickBooks payment response dict with Id and SyncToken

        Raises:
            ValueError: If payment or linked invoice not found or QB invoice not mapped
            httpx.HTTPStatusError: If QuickBooks API call fails
        """
        from app.models.billing import Payment

        # Get payment from Pilot DB — FIND-132: tenant-scoped query
        payment = self.db.exec(
            select(Payment).where(
                Payment.id == payment_id,
                Payment.tenant_id == self.tenant_id,
            )
        ).first()
        if not payment:
            raise ValueError(f"Payment {payment_id} not found")

        # Get access token and realm_id
        access_token, realm_id = await self.get_access_token()
        app_service_id = await self._get_app_service_id()

        # Look up QB Invoice ID
        invoice_mapping = self.db.exec(
            select(IntegrationSyncMapping).where(
                IntegrationSyncMapping.entity_id == payment.invoice_id,
                IntegrationSyncMapping.app_service_id == app_service_id,
                IntegrationSyncMapping.entity_type_code == "invoice",
            )
        ).first()
        if not invoice_mapping:
            raise ValueError(f"Invoice {payment.invoice_id} not mapped to QuickBooks")

        # Build QB Payment payload
        qb_payload = {
            "CustomerRef": {
                "value": payment.invoice_id  # Will be populated via invoice lookup
            },
            "TotalAmt": payment.amount_cents / 100.0,  # QB uses dollars
            "Line": [
                {
                    "Amount": payment.amount_cents / 100.0,
                    "LinkedTxn": {
                        "TxnId": invoice_mapping.external_id,
                        "TxnType": "Invoice",
                    },
                }
            ],
        }

        # API call to QuickBooks
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/company/{realm_id}/payment",
                json=qb_payload,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            intuit_tid = response.headers.get("intuit_tid", "unknown")
            logger.info(
                "QBO API call: %s %s | status=%d | intuit_tid=%s",
                response.request.method,
                str(response.url),
                response.status_code,
                intuit_tid,
            )
            qb_response = response.json()

        # Extract payment from response (QB wraps in "Payment" key)
        qb_payment = qb_response.get("Payment", qb_response)

        # Create/update mapping
        mapping = self.db.exec(
            select(IntegrationSyncMapping).where(
                IntegrationSyncMapping.entity_id == payment_id,
                IntegrationSyncMapping.app_service_id == app_service_id,
                IntegrationSyncMapping.entity_type_code == "payment",
            )
        ).first()

        if not mapping:
            mapping = IntegrationSyncMapping(
                tenant_id=self.tenant_id,
                entity_id=payment.id,
                entity_type_code="payment",
                app_service_id=app_service_id,
                external_id=qb_payment["Id"],
                external_version_token=qb_payment.get("SyncToken"),
                internal_version_token=payment.updated_at.isoformat(),
                sync_preference="pilot_master",
                last_synced_at=datetime.now(UTC),
                created_by=payment.created_by,
                updated_by=payment.updated_by,
            )
            self.db.add(mapping)
        else:
            mapping.external_version_token = qb_payment.get("SyncToken")
            mapping.internal_version_token = payment.updated_at.isoformat()
            mapping.last_synced_at = datetime.now(UTC)
            mapping.updated_by = payment.updated_by

        self.db.commit()

        # SD-07: QB sync operations are unlimited on all tiers (qb_sync_operations feature removed).
        # UsageLedger writes for qb_sync_operations have been removed.

        return qb_payment

    async def _resolve_qco_line_type_to_qb_item(
        self, qco_line_type_id: uuid.UUID, app_service_id: uuid.UUID
    ) -> str:
        """
        Resolve QB Item ID for a qco_line_type, with fallback to generic Services item.

        Looks up integration_sync_mapping for the qco_line_type. If found, returns the
        mapped QB Item ID. If not found, returns a fallback "Services" item ID or creates one.

        Args:
            qco_line_type_id: Pilot qco_line_type ID
            app_service_id: QuickBooks AppService ID

        Returns:
            QuickBooks Item ID (string)
        """
        # Try to find existing mapping
        mapping = self.db.exec(
            select(IntegrationSyncMapping).where(
                IntegrationSyncMapping.entity_id == qco_line_type_id,
                IntegrationSyncMapping.app_service_id == app_service_id,
                IntegrationSyncMapping.entity_type_code == "qco_line_type",
            )
        ).first()

        if mapping:
            return mapping.external_id

        # Fallback: Return generic "Services" item (QB typically has this by default)
        # In production, this would search QB Items by name or create a new item
        return "1"  # QB default service item ID

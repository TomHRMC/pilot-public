"""
GPS variance alert service for FIND-172.

Computes Haversine distance between tech clock-in GPS coordinates
and site address GPS coordinates. If variance exceeds configured threshold,
enqueues notification_outbox row for owner/accountant review.
"""

import logging
import math
import uuid

from sqlalchemy.orm import Session
from sqlmodel import select

from app.models.crm import Address, Site
from app.models.fulfillment import Job
from app.models.system import NotificationEvent, NotificationOutbox
from services.setting_resolver import get_effective_setting

logger = logging.getLogger(__name__)


def compute_haversine_distance_meters(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> int:
    """
    Compute Haversine distance between two GPS coordinates.

    Args:
        lat1, lon1: Tech's clock-in GPS coordinates (decimal degrees)
        lat2, lon2: Site address GPS coordinates (decimal degrees)

    Returns:
        Distance in meters (rounded to nearest integer)

    Formula: Haversine distance = 2 * R * arcsin(sqrt(sin²((lat2-lat1)/2) + cos(lat1) * cos(lat2) * sin²((lon2-lon1)/2)))
    where R = 6,371 km = 6,371,000 meters
    """
    EARTH_RADIUS_METERS = 6_371_000

    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    distance_meters = EARTH_RADIUS_METERS * c
    return int(round(distance_meters))


def check_gps_variance_and_alert(
    db: Session,
    job_id: uuid.UUID,
    tenant_id: uuid.UUID,
    check_in_lat: float | None,
    check_in_lng: float | None,
) -> int | None:
    """
    Check if tech's clock-in GPS coordinates exceed site address variance threshold.

    If variance exceeds threshold, enqueue notification_outbox row for owner/accountant.
    If site address has no GPS coordinates, skip check (return None).

    Args:
        db: Database session
        job_id: UUID of the job being clocked into
        tenant_id: UUID of the tenant
        check_in_lat: Tech's clock-in latitude (from mobile device)
        check_in_lng: Tech's clock-in longitude (from mobile device)

    Returns:
        Variance in meters if computed; None if check skipped (address has no GPS)

    Side effects:
        - Enqueues notification_outbox row if variance > threshold (do NOT commit)
    """

    # If no clock-in GPS provided, skip check
    if check_in_lat is None or check_in_lng is None:
        return None

    # Look up job → site → address
    job = db.exec(
        select(Job).where(Job.id == job_id).where(Job.tenant_id == tenant_id)
    ).first()
    if not job or not job.site_id:
        return None

    site = db.exec(select(Site).where(Site.id == job.site_id)).first()
    if not site:
        return None

    # Get site's primary address
    address = db.exec(
        select(Address)
        .where(Address.id == site.address_id)
        .where(Address.is_active == True)
    ).first()

    # If address has no GPS coordinates, skip check
    if not address or address.latitude is None or address.longitude is None:
        return None

    # Compute Haversine distance
    variance_meters = compute_haversine_distance_meters(
        float(check_in_lat),
        float(check_in_lng),
        float(address.latitude),
        float(address.longitude),
    )

    # Get threshold from platform_setting (post-FIND-086)
    threshold_val, _ = get_effective_setting(
        db, tenant_id, "gps_variance_alert_threshold_meters", fallback=500
    )
    threshold_meters = int(threshold_val)

    # If variance exceeds threshold, enqueue notification
    if variance_meters > threshold_meters:
        _enqueue_gps_variance_alert(
            db, job_id, tenant_id, variance_meters, threshold_meters
        )

    return variance_meters


def _enqueue_gps_variance_alert(
    db: Session,
    job_id: uuid.UUID,
    tenant_id: uuid.UUID,
    variance_meters: int,
    threshold_meters: int,
) -> NotificationOutbox:
    """
    Enqueue notification_outbox row for GPS variance alert.

    Args:
        db: Database session
        job_id: UUID of the job
        tenant_id: UUID of the tenant
        variance_meters: Actual GPS variance computed
        threshold_meters: Configured threshold

    Returns:
        Created NotificationOutbox row (NOT committed — caller owns transaction)

    Note:
        - Uses notification_event='gps_variance_alert' (must exist in DB from seed data)
        - Category 'job_activity' (advisory, non-blocking)
        - Recipients: owner/accountant users (resolved by notification delivery service)
    """

    # Look up the tech's name from job_time_entry (will be added in same transaction)
    # For now, we'll use placeholder; actual tech_name will be known at clock-in time
    # The service will receive it from the caller context
    tech_name = "Technician"
    site_name = "Site"

    job = db.exec(select(Job).where(Job.id == job_id)).first()
    if job and job.site_id:
        site = db.exec(select(Site).where(Site.id == job.site_id)).first()
        if site:
            site_name = site.name or "Site"

    body = (
        f"Tech {tech_name} clocked in {variance_meters}m from {site_name} — "
        f"expected within {threshold_meters}m"
    )

    # Hard lookup — get-or-create fallback removed (SD-2)
    notification_event = db.exec(
        select(NotificationEvent).where(NotificationEvent.code == "gps_variance_alert")
    ).first()

    if not notification_event:
        logger.error(
            "_enqueue_gps_variance_alert: notification_event 'gps_variance_alert' not seeded "
            "— run seed_core.py"
        )
        return None

    # Create notification_outbox row
    # Recipients will be determined by notification delivery service
    # For now, recipient_user_id will be NULL; delivery service will resolve to owner/accountant
    outbox_row = NotificationOutbox(
        notification_event_id=notification_event.id,
        tenant_id=tenant_id,
        recipient_user_id=None,  # Will be resolved by delivery service
        channel="in_app",  # Advisory notification
        body=body,
        category_id="job_activity",
        status="pending",
    )
    db.add(outbox_row)
    return outbox_row

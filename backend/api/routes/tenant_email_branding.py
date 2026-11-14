"""
B15/A82 — Email Branding Endpoints

Routes:
  GET  /api/v1/settings/email-branding          — view current branding
  PUT  /api/v1/settings/email-branding          — update branding
  POST /api/v1/settings/email-branding/logo-upload-url  — get S3 presign URL for logo
  POST /api/v1/settings/email-branding/preview   — preview rendered template
  POST /api/v1/settings/email-branding/test-send — send test email

Auth: JWT required; RBAC: settings.view (GET/preview), settings.manage (PUT/upload/test-send)
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select

from app.models.core import TenantEmailBranding
from core.auth import AuthenticatedUser
from core.db import get_db, set_audit_context_sync
from core.permissions import require_permission
from core.test_context import get_test_context

logger = logging.getLogger(__name__)
router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic schemas
# ─────────────────────────────────────────────────────────────────────────────


class EmailBrandingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tenant_id: uuid.UUID
    logo_url: str | None = None  # resolved URL (not raw S3 path)
    brand_color_hex: str | None = None
    email_signature: str | None = None
    custom_footer: str | None = None


class EmailBrandingUpdate(BaseModel):
    logo_s3_path: str | None = None
    brand_color_hex: str | None = None
    email_signature: str | None = None
    custom_footer: str | None = None


class LogoUploadUrlRequest(BaseModel):
    content_type: str
    file_size_bytes: int


class LogoUploadUrlResponse(BaseModel):
    upload_url: str
    s3_path: str


class PreviewRequest(BaseModel):
    template_id: str = "welcome"


class PreviewResponse(BaseModel):
    subject: str
    body_html: str
    body_plain: str


class TestSendResponse(BaseModel):
    status: str
    to: str


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _resolve_logo_url(s3_path: str | None) -> str | None:
    """Return a presigned GET URL (1 h TTL) so the browser can display the logo
    without requiring the bucket to be public."""
    if not s3_path:
        return None
    from core.config import settings

    bucket = getattr(settings, "S3_BUCKET_NAME", None)
    if not bucket:
        return s3_path  # local stub fallback — no bucket configured

    try:
        import boto3

        s3_client = boto3.client("s3", region_name=settings.AWS_S3_REGION)
        return s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": s3_path},
            ExpiresIn=3600,  # 1 hour
        )
    except Exception as exc:
        logger.warning(f"Could not generate presigned GET URL for logo: {exc}")
        return s3_path  # fallback to raw path rather than returning None


def _branding_to_response(branding: TenantEmailBranding) -> EmailBrandingResponse:
    return EmailBrandingResponse(
        tenant_id=branding.tenant_id,
        logo_url=_resolve_logo_url(branding.logo_s3_path),
        brand_color_hex=branding.brand_color_hex,
        email_signature=branding.email_signature,
        custom_footer=branding.custom_footer,
    )


def _get_or_create_branding(db: Session, tenant_id: uuid.UUID) -> TenantEmailBranding:
    """Get existing branding row or create a blank one."""
    branding = db.exec(
        select(TenantEmailBranding).where(TenantEmailBranding.tenant_id == tenant_id)
    ).first()
    if branding is None:
        branding = TenantEmailBranding(tenant_id=tenant_id)
        db.add(branding)
        db.flush()
    return branding


# ─────────────────────────────────────────────────────────────────────────────
# Shared implementation
# ─────────────────────────────────────────────────────────────────────────────


def _get_branding_impl(db: Session, tenant_id: uuid.UUID) -> EmailBrandingResponse:
    branding = _get_or_create_branding(db, tenant_id)
    db.commit()
    db.refresh(branding)
    return _branding_to_response(branding)


def _update_branding_impl(
    data: EmailBrandingUpdate,
    db: Session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> EmailBrandingResponse:
    set_audit_context_sync(db, user_id)
    branding = _get_or_create_branding(db, tenant_id)

    if data.logo_s3_path is not None:
        branding.logo_s3_path = data.logo_s3_path
    if data.brand_color_hex is not None:
        # Validate hex format
        val = data.brand_color_hex
        if val and (not val.startswith("#") or len(val) not in (4, 7)):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="brand_color_hex must be a valid hex color (#RGB or #RRGGBB)",
            )
        branding.brand_color_hex = data.brand_color_hex
    if data.email_signature is not None:
        if len(data.email_signature) > 500:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="email_signature must be 500 characters or fewer",
            )
        branding.email_signature = data.email_signature
    if data.custom_footer is not None:
        if len(data.custom_footer) > 200:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="custom_footer must be 200 characters or fewer",
            )
        branding.custom_footer = data.custom_footer

    db.add(branding)
    db.commit()
    db.refresh(branding)
    return _branding_to_response(branding)


# ─────────────────────────────────────────────────────────────────────────────
# TEST endpoints (register FIRST)
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/test", response_model=EmailBrandingResponse)
def get_email_branding_test(db: Session = Depends(get_db)):
    """Test endpoint — no auth required."""
    ctx = get_test_context()
    return _get_branding_impl(db, ctx.tenant_id)


# FIND-149: PUT → PATCH (partial-update semantics; all fields Optional in EmailBrandingUpdate)
@router.patch("/test", response_model=EmailBrandingResponse)
def update_email_branding_test(
    data: EmailBrandingUpdate, db: Session = Depends(get_db)
):
    """Test endpoint — no auth required."""
    ctx = get_test_context()
    return _update_branding_impl(data, db, ctx.tenant_id, ctx.id)


@router.post("/test/preview", response_model=PreviewResponse)
def preview_email_branding_test(req: PreviewRequest, db: Session = Depends(get_db)):
    """Test endpoint — no auth required."""
    from services.email_template_renderer import render_preview

    ctx = get_test_context()
    try:
        rendered = render_preview(db, req.template_id, str(ctx.tenant_id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return PreviewResponse(
        subject=rendered.subject,
        body_html=rendered.body_html,
        body_plain=rendered.body_plain,
    )


@router.post("/test/logo-upload-url", response_model=LogoUploadUrlResponse)
def get_logo_upload_url_test(req: LogoUploadUrlRequest, db: Session = Depends(get_db)):
    """Test endpoint — no auth required."""
    ctx = get_test_context()
    s3_path = f"tenant-branding/{ctx.tenant_id}/logo.png"
    return LogoUploadUrlResponse(
        upload_url=f"https://stub-s3.example.com/upload?path={s3_path}",
        s3_path=s3_path,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Authenticated endpoints
# ─────────────────────────────────────────────────────────────────────────────


@router.get("", response_model=EmailBrandingResponse)
def get_email_branding(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("settings.view")),
):
    """Return current email branding configuration for the tenant."""
    return _get_branding_impl(db, current_user.tenant_id)


# FIND-149: PUT → PATCH (partial-update semantics; all fields Optional in EmailBrandingUpdate)
@router.patch("", response_model=EmailBrandingResponse)
def update_email_branding(
    data: EmailBrandingUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("settings.manage")),
):
    """Update email branding configuration for the tenant."""
    return _update_branding_impl(data, db, current_user.tenant_id, current_user.id)


@router.post("/logo-upload-url", response_model=LogoUploadUrlResponse)
def get_logo_upload_url(
    req: LogoUploadUrlRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("settings.manage")),
):
    """
    Generate a pre-signed S3 upload URL for the tenant logo.
    After upload, call PUT /email-branding with s3_path to commit.
    """
    from core.config import settings as cfg

    allowed_types = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}
    if req.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unsupported content type. Allowed: {sorted(allowed_types)}",
        )
    max_size_bytes = 5 * 1024 * 1024  # 5 MB
    if req.file_size_bytes > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Logo file size must be 5 MB or less",
        )

    ext_map = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/webp": "webp",
        "image/gif": "gif",
    }
    ext = ext_map.get(req.content_type, "png")
    s3_path = f"tenant-branding/{current_user.tenant_id}/logo.{ext}"

    # Generate presigned URL (stub if S3 not configured)
    bucket = getattr(cfg, "S3_BUCKET_NAME", None)
    if bucket:
        try:
            import boto3

            s3_client = boto3.client("s3")
            upload_url = s3_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": bucket,
                    "Key": s3_path,
                    "ContentType": req.content_type,
                },
                ExpiresIn=300,  # 5 minutes
            )
        except Exception as e:
            logger.warning(f"S3 presign failed: {e} — returning stub URL")
            upload_url = f"https://stub-s3.example.com/upload?path={s3_path}"
    else:
        upload_url = f"https://stub-s3.example.com/upload?path={s3_path}"

    return LogoUploadUrlResponse(upload_url=upload_url, s3_path=s3_path)


@router.post("/preview", response_model=PreviewResponse)
def preview_email_branding(
    req: PreviewRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("settings.view")),
):
    """
    Render a template with current branding settings without sending.
    Returns rendered subject, body_html, body_plain for UI preview.
    """
    from services.email_template_renderer import render_preview

    try:
        rendered = render_preview(db, req.template_id, str(current_user.tenant_id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return PreviewResponse(
        subject=rendered.subject,
        body_html=rendered.body_html,
        body_plain=rendered.body_plain,
    )


@router.post("/test-send", response_model=TestSendResponse)
def test_send_email(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("settings.manage")),
):
    """
    Send a test email to the requesting user's email address.
    Uses the 'welcome' template with current branding applied.
    """
    # Resolve the user's email
    from app.models.core import User
    from services.email_template_renderer import render_and_send

    user = db.exec(select(User).where(User.id == current_user.id)).first()
    if user is None or not user.email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Could not resolve requesting user's email address",
        )

    try:
        render_and_send(
            db=db,
            template_id="welcome",
            context={"user_name": user.first_name or user.email},
            to_address=user.email,
            tenant_id=str(current_user.tenant_id),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return TestSendResponse(status="sent", to=user.email)

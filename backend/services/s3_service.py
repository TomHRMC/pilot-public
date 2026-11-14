"""
services/s3_service.py

Thin S3 adapter for photo multipart upload pipeline (B7b/A41).
Wraps boto3 S3 calls for mockability in tests via moto.

All S3 operations related to photos route through this module.
Do not call boto3 S3 directly from route or task code.

External dependency status (design doc §G.A41):
    S3 bucket already provisioned. AWS_S3_PHOTOS_BUCKET_NAME must be set in .env.
    AWS credentials come from the execution environment (instance profile or env vars).
"""

from __future__ import annotations

import logging
import math
from typing import Any

import boto3
from botocore.exceptions import ClientError

from core.config import settings

logger = logging.getLogger(__name__)


def _s3_client():
    """Return a boto3 S3 client. Separated for mockability in tests."""
    return boto3.client("s3", region_name=settings.AWS_S3_REGION)


def create_multipart_upload(object_key: str) -> str:
    """
    Initiate an S3 multipart upload session.

    Args:
        object_key: The S3 object key (path) for the file.

    Returns:
        S3 UploadId string (the s3_upload_session_id).

    Raises:
        ClientError: If S3 is unreachable or the bucket doesn't exist.
    """
    client = _s3_client()
    response = client.create_multipart_upload(
        Bucket=settings.AWS_S3_PHOTOS_BUCKET_NAME,
        Key=object_key,
    )
    return response["UploadId"]


def generate_presigned_part_urls(
    object_key: str,
    upload_id: str,
    chunk_count: int,
) -> list[str]:
    """
    Generate presigned URLs for each chunk of a multipart upload.

    Args:
        object_key: The S3 object key.
        upload_id: The S3 multipart UploadId.
        chunk_count: Number of parts (chunks) to generate URLs for.

    Returns:
        List of presigned URLs, one per part (1-indexed part numbers).
    """
    client = _s3_client()
    urls = []
    for part_number in range(1, chunk_count + 1):
        url = client.generate_presigned_url(
            "upload_part",
            Params={
                "Bucket": settings.AWS_S3_PHOTOS_BUCKET_NAME,
                "Key": object_key,
                "UploadId": upload_id,
                "PartNumber": part_number,
            },
            ExpiresIn=settings.AWS_S3_PRESIGNED_URL_EXPIRY_SECONDS,
        )
        urls.append(url)
    return urls


def complete_multipart_upload(
    object_key: str,
    upload_id: str,
    chunk_etags: list[dict[str, Any]],
) -> None:
    """
    Complete an S3 multipart upload by assembling all parts.

    Args:
        object_key: The S3 object key.
        upload_id: The S3 multipart UploadId.
        chunk_etags: List of dicts with 'part_number' and 'etag' keys.

    Raises:
        ClientError: If any part is missing or the UploadId is invalid.
    """
    client = _s3_client()
    parts = [
        {"PartNumber": c["part_number"], "ETag": c["etag"]}
        for c in sorted(chunk_etags, key=lambda x: x["part_number"])
    ]
    client.complete_multipart_upload(
        Bucket=settings.AWS_S3_PHOTOS_BUCKET_NAME,
        Key=object_key,
        UploadId=upload_id,
        MultipartUpload={"Parts": parts},
    )


def abort_multipart_upload(object_key: str, upload_id: str) -> None:
    """
    Abort an orphaned multipart upload session (cleanup task path).

    Args:
        object_key: The S3 object key.
        upload_id: The S3 multipart UploadId to abort.
    """
    try:
        client = _s3_client()
        client.abort_multipart_upload(
            Bucket=settings.AWS_S3_PHOTOS_BUCKET_NAME,
            Key=object_key,
            UploadId=upload_id,
        )
    except ClientError as e:
        # NoSuchUpload is fine — S3 lifecycle rule may have already cleaned it
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code != "NoSuchUpload":
            raise


def compute_chunk_count(file_size_bytes: int) -> int:
    """
    Compute the number of S3 multipart upload parts for a given file size.

    Parts are split at AWS_S3_MULTIPART_CHUNK_SIZE_BYTES (default 5 MB).
    Minimum: 1 part.
    """
    chunk_size = settings.AWS_S3_MULTIPART_CHUNK_SIZE_BYTES
    return max(1, math.ceil(file_size_bytes / chunk_size))


def build_photo_object_key(
    tenant_id: str, job_id: str, attachment_id: str, file_name: str
) -> str:
    """
    Construct the S3 object key for a job photo.

    Pattern: tenants/{tenant_id}/jobs/{job_id}/photos/{attachment_id}/{file_name}

    Args:
        tenant_id: Tenant UUID string.
        job_id: Job UUID string.
        attachment_id: JobAttachment UUID string (the pilot_photo_id).
        file_name: Original file name (e.g. 'site_photo_001.jpg').

    Returns:
        S3 object key string.
    """
    return f"tenants/{tenant_id}/jobs/{job_id}/photos/{attachment_id}/{file_name}"


# ── CE-1: Invoice sign-off signature helpers ──────────────────────────────


def build_signature_object_key(tenant_id: str, invoice_id: str, signoff_id: str) -> str:
    """Return the S3 object key for an invoice sign-off signature PNG.

    Pattern: signatures/{tenant_id}/{invoice_id}/{signoff_id}.png

    Args:
        tenant_id: Tenant UUID string.
        invoice_id: Invoice UUID string.
        signoff_id: InvoiceSignoff UUID string.

    Returns:
        S3 object key string (cf. build_photo_object_key).
    """
    return f"signatures/{tenant_id}/{invoice_id}/{signoff_id}.png"


def put_signature_object(object_key: str, png_bytes: bytes) -> None:
    """Upload a signature PNG to the photos bucket.

    Server-side put_object to the same bucket constant used by
    create_multipart_upload; ContentType='image/png'.

    Args:
        object_key: S3 object key from build_signature_object_key().
        png_bytes: Decoded PNG file bytes.

    Raises:
        ClientError: If S3 is unreachable or the bucket doesn't exist.
            The caller maps this to a 502 RFC 7807 problem detail.
    """
    client = _s3_client()
    client.put_object(
        Bucket=settings.AWS_S3_PHOTOS_BUCKET_NAME,
        Key=object_key,
        Body=png_bytes,
        ContentType="image/png",
    )


def generate_presigned_get_url(object_key: str, expires_in: int = 3600) -> str:
    """Generate a presigned GET URL for a signature object.

    Presigned GET against the photos bucket (precedent: user_profile.py
    get_object call). Centralizes the 3 existing ad-hoc call sites' pattern.

    Args:
        object_key: S3 object key.
        expires_in: URL TTL in seconds (default 1 hour).

    Returns:
        Presigned GET URL string.
    """
    client = _s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.AWS_S3_PHOTOS_BUCKET_NAME,
            "Key": object_key,
        },
        ExpiresIn=expires_in,
    )

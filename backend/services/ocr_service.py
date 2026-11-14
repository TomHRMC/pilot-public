"""
services/ocr_service.py

Receipt OCR service adapter for the FIND-062/B21/A96 OCR pipeline.

Architecture:
  - OcrService (ABC): interface for all OCR backends
  - RapidOcrService: production — uses rapidocr-onnxruntime (CPU inference on ECS Fargate)
  - MockOcrService: test/dev — returns deterministic fixture data; never calls RapidOCR

GPU note: Do NOT route this to the g4dn.xlarge GPU instance.
GPU is reserved for Whisper + Ollama (already at ~6.2GB/16GB VRAM).
RapidOCR runs CPU inference in the ECS Fargate app container.
CPU inference < 2 seconds for receipt images. Zero cloud cost.

S3 download: uses AWS_S3_PHOTOS_BUCKET_NAME via boto3 (same credential path as photo uploads).

Factory:
  - get_ocr_service() → MockOcrService when ENVIRONMENT='dev'/'qa' and TEST_ENDPOINT_ENABLED=True
  - get_ocr_service() → RapidOcrService in staging/production
"""

from __future__ import annotations

import logging
import re
import tempfile
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class OcrService(ABC):
    """Abstract base class for receipt OCR backends."""

    @abstractmethod
    def extract_expense(self, s3_key: str) -> dict | None:
        """
        Extract expense data from a receipt image stored in S3.

        Args:
            s3_key: S3 object key for the receipt image.

        Returns:
            dict with keys: total_cents (int), vendor (str), date (str), line_items (list)
            or None if confidence is below the acceptance threshold.
        """
        ...


class RapidOcrService(OcrService):
    """
    Production OCR backend using rapidocr-onnxruntime (CPU inference).

    Downloads the receipt image from S3 to a temp file, runs RapidOCR,
    and parses the extracted text for expense total.

    Confidence threshold: 0.7 (returns None if best match confidence < 0.7).
    """

    # Regex patterns for total extraction — ordered by specificity
    _TOTAL_PATTERNS = [
        re.compile(
            r"(?:total|amount\s+due|grand\s+total|balance\s+due)[^\d]*\$?\s*([\d,]+\.?\d*)",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:subtotal|sub\s+total)[^\d]*\$?\s*([\d,]+\.?\d*)", re.IGNORECASE
        ),
        re.compile(r"\$\s*([\d,]+\.\d{2})\s*$", re.IGNORECASE | re.MULTILINE),
    ]

    _VENDOR_PATTERNS = [
        re.compile(r"^([A-Z][A-Za-z0-9\s&',.-]{2,40})$", re.MULTILINE),
    ]

    _DATE_PATTERNS = [
        re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b"),
        re.compile(r"\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b"),
    ]

    def extract_expense(self, s3_key: str) -> dict | None:
        """
        Download receipt from S3, run RapidOCR, parse expense data.

        Returns None if:
          - S3 download fails
          - No text detected
          - No total found in parsed text
          - Confidence below 0.7 threshold
        """
        try:
            import boto3

            from core.config import settings

            s3 = boto3.client("s3", region_name=settings.AWS_S3_REGION)
            bucket = settings.AWS_S3_PHOTOS_BUCKET_NAME

            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=True) as tmp:
                try:
                    s3.download_file(bucket, s3_key, tmp.name)
                except Exception as e:
                    logger.warning("OCR: S3 download failed for key=%s: %s", s3_key, e)
                    return None

                return self._run_ocr(tmp.name)

        except Exception as e:
            logger.error("OCR: Unexpected error for s3_key=%s: %s", s3_key, e)
            return None

    def _run_ocr(self, image_path: str) -> dict | None:
        """Run RapidOCR on a local image file and parse result."""
        try:
            from rapidocr_onnxruntime import RapidOCR  # type: ignore[import]
        except ImportError:
            logger.error(
                "OCR: rapidocr-onnxruntime not installed. Add to requirements.txt."
            )
            return None

        try:
            ocr = RapidOCR()
            result, _ = ocr(image_path)
        except Exception as e:
            logger.warning("OCR: RapidOCR inference failed: %s", e)
            return None

        if not result:
            logger.debug("OCR: No text detected in image %s", image_path)
            return None

        # Filter by confidence threshold
        MIN_CONFIDENCE = 0.7
        lines = []
        for item in result:
            if len(item) >= 3:
                text, confidence = item[1], item[2]
                if confidence >= MIN_CONFIDENCE:
                    lines.append(text)
            elif len(item) >= 2:
                lines.append(item[1])

        if not lines:
            logger.debug("OCR: No lines passed confidence threshold for %s", image_path)
            return None

        full_text = "\n".join(lines)
        return self._parse_receipt_text(full_text, lines)

    def _parse_receipt_text(self, full_text: str, lines: list[str]) -> dict | None:
        """Parse OCR text to extract total, vendor, date."""
        # Extract total
        total_cents = None
        for pattern in self._TOTAL_PATTERNS:
            match = pattern.search(full_text)
            if match:
                try:
                    amount_str = match.group(1).replace(",", "")
                    total_cents = round(float(amount_str) * 100)
                    break
                except (ValueError, IndexError):
                    continue

        if total_cents is None:
            logger.debug("OCR: Could not extract total from receipt text")
            return None

        # Extract vendor (first non-empty line that looks like a name)
        vendor = None
        for line in lines[:5]:  # Check first 5 lines for vendor name
            line = line.strip()
            if len(line) >= 3 and not re.match(r"^\d", line):
                vendor = line
                break

        # Extract date
        date = None
        for pattern in self._DATE_PATTERNS:
            match = pattern.search(full_text)
            if match:
                date = match.group(1)
                break

        return {
            "total_cents": total_cents,
            "vendor": vendor or "",
            "date": date or "",
            "line_items": [],
        }


class MockOcrService(OcrService):
    """
    Test/dev OCR backend. Returns deterministic fixture data.

    Never calls RapidOCR or boto3. Safe for unit tests without S3 credentials.

    Behavior:
      - S3 keys containing 'low_confidence' → returns None (simulates below-threshold result)
      - All other S3 keys → returns fixture expense data
    """

    # Fixture data for predictable tests
    FIXTURE_RESULT = {
        "total_cents": 4250,  # $42.50
        "vendor": "Electrical Supply Co",
        "date": "2026-05-19",
        "line_items": [
            {"description": "20A Circuit Breaker", "amount_cents": 3500},
            {"description": "Wire connectors", "amount_cents": 750},
        ],
    }

    def extract_expense(self, s3_key: str) -> dict | None:
        """Return fixture data or None based on s3_key."""
        if "low_confidence" in s3_key or "no_receipt" in s3_key:
            logger.debug("MockOcrService: returning None for key=%s", s3_key)
            return None

        logger.debug("MockOcrService: returning fixture data for key=%s", s3_key)
        return dict(self.FIXTURE_RESULT)


def get_ocr_service() -> OcrService:
    """
    Factory function for OCR service.

    Returns:
        MockOcrService when ENVIRONMENT is 'dev' or 'qa' (test mode)
        RapidOcrService in staging or production
    """
    try:
        from core.config import settings

        if settings.ENVIRONMENT in ("dev", "qa"):
            return MockOcrService()
    except Exception:
        pass

    return RapidOcrService()

# ─── S3: Assets Bucket (audio, receipt images, PDF exports) ──────────────────

resource "aws_s3_bucket" "assets" {
  # Account ID suffix required — "pilot-production-assets" is taken globally
  bucket = "pilot-${var.environment}-assets-${var.account_id}"

  tags = {
    Name               = "pilot-${var.environment}-assets-${var.account_id}"
    Component          = "asset-storage"
    CostAllocation     = "web-infrastructure"
    DataClassification = "sensitive"
    Backup             = "enabled"
  }
}

resource "aws_s3_bucket_versioning" "assets" {
  bucket = aws_s3_bucket.assets.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_arn
    }
    bucket_key_enabled = true # Reduces KMS API calls and costs
  }
}

resource "aws_s3_bucket_public_access_block" "assets" {
  bucket = aws_s3_bucket.assets.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id

  rule {
    id     = "audio-files-lifecycle"
    status = "Enabled"

    filter {
      prefix = "audio/"
    }

    # Transition old audio files to cheaper storage after 90 days
    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }

    # Move to Glacier after 1 year
    transition {
      days          = 365
      storage_class = "GLACIER"
    }
  }

  rule {
    id     = "incomplete-multipart-cleanup"
    status = "Enabled"

    filter {
      prefix = ""
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# ─── S3: Marketing Site (static HTML/CSS/JS, CloudFront origin) ───────────────

resource "aws_s3_bucket" "marketing" {
  bucket = "pilot-${var.environment}-marketing"

  tags = {
    Name               = "pilot-${var.environment}-marketing"
    Component          = "marketing-site"
    CostAllocation     = "marketing"
    DataClassification = "public"
    Backup             = "disabled"
  }
}

resource "aws_s3_bucket_versioning" "marketing" {
  bucket = aws_s3_bucket.marketing.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Marketing bucket uses S3-managed keys (not KMS) since content is public anyway
resource "aws_s3_bucket_server_side_encryption_configuration" "marketing" {
  bucket = aws_s3_bucket.marketing.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block direct public access — CloudFront OAC handles delivery
resource "aws_s3_bucket_public_access_block" "marketing" {
  bucket = aws_s3_bucket.marketing.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Bucket policy allowing CloudFront OAC to read objects
# Note: cloudfront_oac_arn is provided by compute module after CloudFront distribution is created
# This creates a dependency cycle — in practice, apply storage first, then compute,
# then apply storage again to update the bucket policy with the OAC ARN.
resource "aws_s3_bucket_policy" "marketing" {
  bucket = aws_s3_bucket.marketing.id
  policy = data.aws_iam_policy_document.marketing_bucket.json
}

data "aws_iam_policy_document" "marketing_bucket" {
  statement {
    sid    = "AllowCloudFrontOACAccess"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.marketing.arn}/*"]

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [var.cloudfront_oac_arn != "" ? var.cloudfront_oac_arn : "arn:aws:cloudfront::${var.account_id}:distribution/PLACEHOLDER"]
    }
  }
}

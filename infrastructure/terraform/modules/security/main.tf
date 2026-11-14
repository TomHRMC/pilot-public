# ─── KMS Customer-Managed Key ─────────────────────────────────────────────────

resource "aws_kms_key" "pilot" {
  description             = "Pilot for Trades - ${var.environment} encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true # Annual automatic rotation

  tags = {
    Name               = "pilot-${var.environment}-cmk"
    Component          = "secrets-security"
    CostAllocation     = "security-monitoring"
    DataClassification = "sensitive"
    Backup             = "disabled"
  }
}

resource "aws_kms_alias" "pilot" {
  name          = "alias/pilot-${var.environment}"
  target_key_id = aws_kms_key.pilot.key_id
}

# ─── Secrets Manager — Secret Shells ─────────────────────────────────────────
# Secret shells are created here (security module).
# Actual values are populated by:
#   - database module (db, redis)
#   - manual AWS Console entry (quickbooks, stripe — require human action)
#   - already populated via Console (sendgrid, telnyx, encryption, google-maps, cognito, turnstile)
#
# Secret naming convention: pilot/prod/<service>
# Rotation: manual (no automatic rotation is configured; quarterly RDS rotation was planned)

resource "aws_secretsmanager_secret" "db" {
  name                    = "pilot/prod/db"
  description             = "RDS PostgreSQL credentials - username, password, host, port, dbname, url"
  kms_key_id              = aws_kms_key.pilot.arn
  recovery_window_in_days = 30

  tags = {
    Component          = "secrets-security"
    CostAllocation     = "security-monitoring"
    DataClassification = "sensitive"
  }
}

resource "aws_secretsmanager_secret" "redis" {
  name                    = "pilot/prod/redis"
  description             = "ElastiCache Redis connection info - host, port, broker_url, result_url, rate_url"
  kms_key_id              = aws_kms_key.pilot.arn
  recovery_window_in_days = 7

  tags = {
    Component          = "secrets-security"
    CostAllocation     = "security-monitoring"
    DataClassification = "sensitive"
  }
}

resource "aws_secretsmanager_secret" "gpu" {
  name                    = "pilot/prod/gpu"
  description             = "GPU instance internal URLs - whisper_url, ollama_url (populated after Phase 4 GPU deploy)"
  kms_key_id              = aws_kms_key.pilot.arn
  recovery_window_in_days = 7

  tags = {
    Component          = "secrets-security"
    CostAllocation     = "security-monitoring"
    DataClassification = "sensitive"
  }
}

resource "aws_secretsmanager_secret" "quickbooks" {
  name                    = "pilot/prod/quickbooks"
  description             = "QuickBooks PRODUCTION app credentials - client_id, client_secret, webhook_verifier_token, environment. MANUAL ENTRY REQUIRED."
  kms_key_id              = aws_kms_key.pilot.arn
  recovery_window_in_days = 30

  tags = {
    Component          = "secrets-security"
    CostAllocation     = "security-monitoring"
    DataClassification = "sensitive"
  }
}

resource "aws_secretsmanager_secret" "sendgrid" {
  name                    = "pilot/prod/sendgrid"
  description             = "SendGrid API key - key name: PilotForTrades-Prod; from_email: noreply@pilotfortrades.com. ALREADY CREATED via Console."
  kms_key_id              = aws_kms_key.pilot.arn
  recovery_window_in_days = 30

  tags = {
    Component          = "secrets-security"
    CostAllocation     = "security-monitoring"
    DataClassification = "sensitive"
  }
}

resource "aws_secretsmanager_secret" "telnyx" {
  name                    = "pilot/prod/telnyx"
  description             = "Telnyx API key - messaging_profile_id: 00000000-0000-0000-0000-000000000000. ALREADY CREATED via Console."
  kms_key_id              = aws_kms_key.pilot.arn
  recovery_window_in_days = 30

  tags = {
    Component          = "secrets-security"
    CostAllocation     = "security-monitoring"
    DataClassification = "sensitive"
  }
}

resource "aws_secretsmanager_secret" "stripe" {
  name                    = "pilot/prod/stripe"
  description             = "Stripe live mode keys - publishable_key, secret_key, webhook_secret. MANUAL ENTRY REQUIRED: switch to live mode in Stripe dashboard."
  kms_key_id              = aws_kms_key.pilot.arn
  recovery_window_in_days = 30

  tags = {
    Component          = "secrets-security"
    CostAllocation     = "security-monitoring"
    DataClassification = "sensitive"
  }
}

resource "aws_secretsmanager_secret" "encryption" {
  name                    = "pilot/prod/encryption"
  description             = "Fernet encryption key for field-level encryption. ALREADY CREATED via Console. NEVER log or print this value."
  kms_key_id              = aws_kms_key.pilot.arn
  recovery_window_in_days = 30

  tags = {
    Component          = "secrets-security"
    CostAllocation     = "security-monitoring"
    DataClassification = "sensitive"
  }
}

resource "aws_secretsmanager_secret" "cognito" {
  name                    = "pilot/prod/cognito"
  description             = "Production Cognito config - region, user_pool_id, app_client_id"
  kms_key_id              = aws_kms_key.pilot.arn
  recovery_window_in_days = 7

  tags = {
    Component          = "secrets-security"
    CostAllocation     = "security-monitoring"
    DataClassification = "sensitive"
  }
}

# Populate Cognito secret with known prod values
resource "aws_secretsmanager_secret_version" "cognito" {
  secret_id = aws_secretsmanager_secret.cognito.id
  secret_string = jsonencode({
    region        = var.aws_region
    user_pool_id  = var.cognito_user_pool_id
    app_client_id = var.cognito_app_client_id
  })
}

resource "aws_secretsmanager_secret" "google_maps" {
  name                    = "pilot/prod/google-maps"
  description             = "Google Maps Distance Matrix API key - key name: PilotForTrades-Prod. ALREADY CREATED. Restrict IP to NAT Gateway EIP after Phase 1."
  kms_key_id              = aws_kms_key.pilot.arn
  recovery_window_in_days = 30

  tags = {
    Component          = "secrets-security"
    CostAllocation     = "security-monitoring"
    DataClassification = "sensitive"
  }
}

resource "aws_secretsmanager_secret" "turnstile" {
  name                    = "pilot/prod/turnstile"
  description             = "Cloudflare Turnstile server-side secret key for marketing form verification. ALREADY CREATED via Console."
  kms_key_id              = aws_kms_key.pilot.arn
  recovery_window_in_days = 30

  tags = {
    Component          = "secrets-security"
    CostAllocation     = "security-monitoring"
    DataClassification = "sensitive"
  }
}

# ─── IAM: ECS Task Role (app permissions) ─────────────────────────────────────

resource "aws_iam_role" "ecs_task" {
  name = "pilot-${var.environment}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = {
    Component      = "secrets-security"
    CostAllocation = "security-monitoring"
  }
}

resource "aws_iam_role_policy" "ecs_task_secrets" {
  name = "pilot-${var.environment}-ecs-task-secrets"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SecretsManagerAccess"
        Effect = "Allow"
        Action = ["secretsmanager:GetSecretValue"]
        # Least-privilege: only the secrets this app needs
        Resource = [
          aws_secretsmanager_secret.db.arn,
          aws_secretsmanager_secret.redis.arn,
          aws_secretsmanager_secret.gpu.arn,
          aws_secretsmanager_secret.quickbooks.arn,
          aws_secretsmanager_secret.sendgrid.arn,
          aws_secretsmanager_secret.telnyx.arn,
          aws_secretsmanager_secret.stripe.arn,
          aws_secretsmanager_secret.encryption.arn,
          aws_secretsmanager_secret.cognito.arn,
          aws_secretsmanager_secret.google_maps.arn,
          aws_secretsmanager_secret.turnstile.arn,
        ]
      },
      {
        Sid      = "KMSDecrypt"
        Effect   = "Allow"
        Action   = ["kms:Decrypt", "kms:GenerateDataKey"]
        Resource = [aws_kms_key.pilot.arn]
      },
      {
        Sid    = "S3AssetAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:GetObjectVersion",
        ]
        # Assets bucket ARN injected from storage module output
        Resource = var.assets_bucket_arn != "" ? [
          "${var.assets_bucket_arn}/*"
        ] : ["arn:aws:s3:::pilot-${var.environment}-assets/*"]
      },
      {
        Sid    = "S3AssetsBucketList"
        Effect = "Allow"
        Action = ["s3:ListBucket"]
        Resource = var.assets_bucket_arn != "" ? [
          var.assets_bucket_arn
        ] : ["arn:aws:s3:::pilot-${var.environment}-assets"]
      },
      {
        Sid    = "XRayTracing"
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords",
          "xray:GetSamplingRules",
          "xray:GetSamplingTargets",
        ]
        Resource = ["*"]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_cloudwatch" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
}

# ─── IAM: ECS Execution Role (ECR pull + CloudWatch logging) ─────────────────

resource "aws_iam_role" "ecs_execution" {
  name = "pilot-${var.environment}-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = {
    Component      = "secrets-security"
    CostAllocation = "security-monitoring"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_execution_managed" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Allow execution role to fetch secrets for injection into task environment
resource "aws_iam_role_policy" "ecs_execution_secrets" {
  name = "pilot-${var.environment}-ecs-execution-secrets"
  role = aws_iam_role.ecs_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SecretsManagerRead"
        Effect = "Allow"
        Action = ["secretsmanager:GetSecretValue"]
        Resource = [
          aws_secretsmanager_secret.db.arn,
          aws_secretsmanager_secret.redis.arn,
          aws_secretsmanager_secret.gpu.arn,
          aws_secretsmanager_secret.quickbooks.arn,
          aws_secretsmanager_secret.sendgrid.arn,
          aws_secretsmanager_secret.telnyx.arn,
          aws_secretsmanager_secret.stripe.arn,
          aws_secretsmanager_secret.encryption.arn,
          aws_secretsmanager_secret.cognito.arn,
          aws_secretsmanager_secret.google_maps.arn,
          aws_secretsmanager_secret.turnstile.arn,
        ]
      },
      {
        Sid      = "KMSDecrypt"
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = [aws_kms_key.pilot.arn]
      }
    ]
  })
}

# ─── IAM: Lambda Execution Role ───────────────────────────────────────────────

resource "aws_iam_role" "lambda_execution" {
  name = "pilot-${var.environment}-lambda-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = {
    Component      = "secrets-security"
    CostAllocation = "security-monitoring"
  }
}

resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy" "lambda_rds" {
  name = "pilot-${var.environment}-lambda-rds"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SecretsManagerRead"
        Effect = "Allow"
        Action = ["secretsmanager:GetSecretValue"]
        # Least-privilege (secret-management-policy §4): only the secrets the
        # Cognito Lambdas fetch at runtime. The redis ARN was added for
        # PLATFORM-SMS-B2 (Post-Authentication Lambda broker resolution).
        # Do NOT wildcard the ARN; do NOT rename the policy (rename = recreate).
        Resource = [
          aws_secretsmanager_secret.db.arn,
          aws_secretsmanager_secret.redis.arn,
        ]
      },
      {
        Sid      = "KMSDecrypt"
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = [aws_kms_key.pilot.arn]
      }
    ]
  })
}

# ─── IAM: GitHub Actions OIDC ─────────────────────────────────────────────────

resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = ["sts.amazonaws.com"]

  # GitHub's OIDC thumbprint (stable; changes only if GitHub rotates their cert)
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

resource "aws_iam_role" "github_actions" {
  name = "pilot-${var.environment}-github-actions"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.github.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          # repo:TomHRMC/pilot:* allows all branches and workflow triggers
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_repo}:*"
        }
      }
    }]
  })

  tags = {
    Component      = "secrets-security"
    CostAllocation = "security-monitoring"
  }
}

resource "aws_iam_role_policy" "github_actions_deploy" {
  name = "pilot-${var.environment}-github-actions-deploy"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ECRAuth"
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = ["*"]
      },
      {
        Sid    = "ECRPush"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
        ]
        Resource = [
          "arn:aws:ecr:${var.aws_region}:${var.account_id}:repository/pilot/*"
        ]
      },
      {
        Sid    = "ECSDeployServices"
        Effect = "Allow"
        Action = [
          "ecs:UpdateService",
          "ecs:DescribeServices",
          "ecs:DescribeTaskDefinition",
          "ecs:RegisterTaskDefinition",
          "ecs:RunTask",
          "ecs:DescribeTasks",
          "ecs:ListTasks",
        ]
        Resource = ["*"]
      },
      {
        Sid    = "PassRoleForECS"
        Effect = "Allow"
        Action = ["iam:PassRole"]
        Resource = [
          aws_iam_role.ecs_task.arn,
          aws_iam_role.ecs_execution.arn,
        ]
      },
      {
        Sid    = "S3MarketingDeploy"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket",
        ]
        Resource = [
          "arn:aws:s3:::pilot-${var.environment}-marketing",
          "arn:aws:s3:::pilot-${var.environment}-marketing/*",
        ]
      },
      {
        Sid      = "CloudFrontInvalidate"
        Effect   = "Allow"
        Action   = ["cloudfront:CreateInvalidation"]
        Resource = ["arn:aws:cloudfront::${var.account_id}:distribution/*"]
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:GetLogEvents",
          "logs:DescribeLogStreams",
          "logs:DescribeLogGroups",
        ]
        Resource = ["*"]
      }
    ]
  })
}

# ─── Route 53 Hosted Zone ─────────────────────────────────────────────────────

resource "aws_route53_zone" "main" {
  name = var.domain_name

  tags = {
    Name           = "pilot-${var.environment}-zone"
    Component      = "dns"
    CostAllocation = "networking"
  }
}

# ─── ACM Wildcard Certificate (must be us-east-1 for CloudFront) ─────────────

resource "aws_acm_certificate" "wildcard" {
  domain_name               = var.domain_name
  subject_alternative_names = ["*.${var.domain_name}"]
  validation_method         = "DNS"

  tags = {
    Name           = "pilot-${var.environment}-cert"
    Component      = "dns"
    CostAllocation = "networking"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# ACM DNS validation records in Route 53
resource "aws_route53_record" "acm_validation" {
  for_each = {
    for dvo in aws_acm_certificate.wildcard.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = aws_route53_zone.main.zone_id
}

# aws_acm_certificate_validation.wildcard is intentionally omitted here.
# The ACM cert is created above (PENDING_VALIDATION status).
# Validation completes automatically after Phase 5 GoDaddy → Route 53 NS cutover.
# The cert ARN is usable in resource configs immediately; ALB/CloudFront will wait
# for validation before serving HTTPS (AWS handles this gracefully).

# ─── ACM Wildcard Certificate for p4tsites.com (C-B16-OPS, ADR-0014) ──────────
# Tenant-sites domain cert. apex + wildcard SAN.
# Validation is DNS, records created MANUALLY in Cloudflare (Step 2) —
# no aws_acm_certificate_validation resource (same posture as the wildcard above).
# No Route 53 hosted zone for this domain (ADR-0014 — DNS lives in Cloudflare).
resource "aws_acm_certificate" "p4tsites" {
  domain_name               = "p4tsites.com"
  subject_alternative_names = ["*.p4tsites.com"]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name      = "p4tsites-wildcard"
    Component = "tenant-sites"
  }
}

# aws_acm_certificate_validation.p4tsites is intentionally omitted — same posture
# as the pilotfortrades wildcard above. Validation CNAMEs are created manually in
# Cloudflare (C-B16-OPS Step 2). The cert ARN is usable immediately; the ALB SNI
# listener certificate will wait for ISSUED status before serving HTTPS.

# ─── Route 53: Google Workspace Email Records ─────────────────────────────────
# IMPORTANT: Add these BEFORE updating nameservers at GoDaddy to avoid email outage.
# Values below are standard Google Workspace MX records.
# Copy DKIM and DMARC values from GoDaddy before NS cutover.

resource "aws_route53_record" "mx" {
  zone_id = aws_route53_zone.main.zone_id
  name    = var.domain_name
  type    = "MX"
  ttl     = 3600
  records = [
    "1 aspmx.l.google.com",
    "5 alt1.aspmx.l.google.com",
    "5 alt2.aspmx.l.google.com",
    "10 alt3.aspmx.l.google.com",
    "10 alt4.aspmx.l.google.com",
  ]
}

# Apex TXT records: SPF + Google site verification
# Multiple TXT values on the same name MUST be in the same Route 53 record resource
resource "aws_route53_record" "apex_txt" {
  zone_id = aws_route53_zone.main.zone_id
  name    = var.domain_name
  type    = "TXT"
  ttl     = 3600
  records = [
    "v=spf1 include:_spf.google.com ~all",
    "google-site-verification=<token>",
  ]
}

# Google Workspace DKIM — selector: "google" (set up 2026-07-01)
# Source: GoDaddy zone export pilotfortrades.com.txt
# Record type: TXT at google._domainkey (NOT CNAME — Google Workspace uses TXT for DKIM)
# Long key split in DNS wire format; Terraform concatenates automatically
# DKIM — split into two list entries; each entry ≤255 chars.
# Terraform AWS provider wraps each records entry in quotes automatically.
# Multiple entries in records[] for TXT = multiple character-strings in the SAME TXT RRset.
# Resolvers concatenate them: "chunk1" "chunk2" → valid DKIM key.
# Exact split computed: prefix "v=DKIM1; k=rsa; p=" = 18 chars; key chars in chunk1 = 237; chunk1 total = 255 chars.
resource "aws_route53_record" "dkim" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "google._domainkey.${var.domain_name}"
  type    = "TXT"
  ttl     = 3600
  records = [
    "v=DKIM1; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAqQ6tUAs7iiILmQzsMuG4wYD6OO5qElnXiLWQdLPPzaO3vdALVroNliDVrS7RD5TX5W75VwW3fD/sgDwKEEZPKbfRkx6c5Y2roi/pUpEkNdWB3rZ/SiHlVSIw6raaw0CFfMQE+f3stcXnkgopCJfGQQuLGt/+NE/K5A5MF9U0sKqnFbdnVDqT/a0M2tLIaJjHM\" \"37ox2O2f2zbKpE+gZnz7ys+tW5vNCSSAYpRlB93CzkAbg3c6qCkZU3LUohPpPJoV5UDkBsNAsT3z9WTwDiNC6H7rlUrW0c18AZfsfpF75THqE4U74huA4MvkdLA62qoY9gKtwnYfbJDGr53t8JKtQIDAQAB"
  ]
}

# DMARC — policy: quarantine; reporting to legal@pilotfortrades.com (updated from GoDaddy default)
# Source: GoDaddy zone export; RUA updated from dmarc_rua@onsecureserver.net → legal@
resource "aws_route53_record" "dmarc" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "_dmarc.${var.domain_name}"
  type    = "TXT"
  ttl     = 3600
  records = ["v=DMARC1; p=quarantine; adkim=r; aspf=r; rua=mailto:legal@pilotfortrades.com;"]
}

# ─── Cognito User Pool (import existing — us-east-1_XXXXXXXXX) ───────────────
# ⚠️  Do NOT apply this block until AFTER running:
#   terraform import aws_cognito_user_pool.prod us-east-1_XXXXXXXXX
#   terraform import aws_cognito_user_pool_client.prod_web us-east-1_XXXXXXXXX/xxxxxxxxxxxxxxxxxxxxxxxxxx
#
# Pool was created manually via Console on 2026-06-30 per aws-cognito-prod-setup.md

# MFA-WIRE-1 (Step 0): Cognito SMS delivery — SNS role + SmsConfiguration.
# The pool was console-created (2026-06-30) without an SNS role, so SMS MFA
# OTPs could never be delivered (design §0 row 9). Terraform-managed from here.
# The ExternalId is a configuration value (not a secret) — it lives in this
# module's variables, not in Secrets Manager (secret-management-policy §1).
resource "aws_iam_role" "cognito_sns" {
  name = "CognitoSNSRole-pilot-production" # matches the console-era setup-doc name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCognitoIdpAssume"
        Effect    = "Allow"
        Principal = { Service = "cognito-idp.amazonaws.com" }
        Action    = "sts:AssumeRole"
        Condition = {
          StringEquals = { "sts:ExternalId" = var.cognito_sms_external_id }
        }
      }
    ]
  })

  tags = {
    Component          = "auth"
    CostAllocation     = "security-monitoring"
    DataClassification = "sensitive"
  }
}

resource "aws_iam_role_policy" "cognito_sns_publish" {
  name = "cognito-sns-sms-publish"
  role = aws_iam_role.cognito_sns.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowSnsPublishForSms"
        Effect = "Allow"
        Action = "sns:Publish"
        # SNS phone-number-targeted SMS publish has no resource-level scoping —
        # AWS's own Cognito SMS role documentation uses "*". This is the
        # documented, least-privilege-available form for Cognito SMS delivery.
        Resource = "*"
      }
    ]
  })
}

resource "aws_cognito_user_pool" "prod" {
  name = "pilot-production"

  # Preserve the production auth pool — never allow accidental deletion.
  # (Was set in AWS console; added to config to prevent Terraform flipping it
  # to INACTIVE on the next apply — SIGNUP-GA-1 safety fix.)
  deletion_protection = "ACTIVE"

  # MFA-WIRE-1 tail (2026-08-25): branded SMS templates, set in console and
  # codified here in the same change (C-B16-OPS Step 0). Email verification
  # template intentionally left at Cognito default — COGNITO-EMAIL-1 owns it.
  sms_authentication_message = "Your Pilot for Trades authentication code is {####}. It expires in 5 minutes."
  sms_verification_message   = "Your Pilot for Trades verification code is {####}. It expires in 24 hours."

  # Email sign-in only
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  # ADR-0011 (SIGNUP-GA-1): self-service signup ENABLED — clients call Cognito
  # SignUp (email+password) via Amplify; the Post-Confirmation Lambda provisions
  # RDS rows. Email verification is required before the trigger fires (gate).
  # Rollback: set this to true to re-close self-registration (existing users unaffected).
  admin_create_user_config {
    allow_admin_create_user_only = false
  }

  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = true
    temporary_password_validity_days = 7
  }

  mfa_configuration = "OPTIONAL"

  software_token_mfa_configuration {
    enabled = true
  }

  # MFA-WIRE-1 (Step 0): SMS MFA delivery path via SNS role. SMS templates
  # codified above (2026-08-25). The pool had TOTP + SMS factors enabled at the
  # console but no SmsConfiguration, so Cognito could not deliver SMS OTPs
  # (InvalidSmsRole*Exception on enrollment). This wires the SNS role above.
  sms_configuration {
    external_id    = var.cognito_sms_external_id
    sns_caller_arn = aws_iam_role.cognito_sns.arn
    sns_region     = "us-east-1"
  }

  lambda_config {
    post_confirmation = aws_lambda_function.post_confirmation.arn
  }

  user_pool_add_ons {
    advanced_security_mode = "AUDIT"
  }

  tags = {
    Component          = "auth"
    CostAllocation     = "security-monitoring"
    DataClassification = "sensitive"
  }

  # Prevent forced replacement when lambda_config, name, or other computed attributes
  # differ from the manually-created pool (created via Console as "pilot - prod").
  # user_pool_add_ons: pool is on ESSENTIALS tier — advanced_security_mode not supported.
  #
  # SIGNUP-GA-1 (ADR-0011): lambda_config stays in ignore_changes deliberately.
  # The Post-Confirmation trigger is wired MANUALLY via CLI after the Lambda
  # deploys (see aws-ops-runbook.md §14.5). Letting Terraform manage lambda_config
  # risks removing other manually-configured triggers or forcing pool replacement
  # — unacceptable for auth-critical infra. The aws_lambda_permission resource
  # below grants Cognito invoke rights; the trigger attachment itself is CLI.
  #
  # PLATFORM-SMS-B2 (ADR-0013): device_configuration stays in ignore_changes for
  # the same reason — it is wired MANUALLY via CLI (alongside both Lambda triggers
  # in one update-user-pool call, because --device-configuration and --lambda-config
  # must be passed together or the omitted block is silently cleared). Letting
  # Terraform manage it would strip the "Always remember" tracking that populates
  # newDeviceUsed for the Post-Authentication new-device alert gate.
  lifecycle {
    ignore_changes = [
      lambda_config,
      device_configuration,
      schema,
      username_configuration,
      name,
      user_pool_add_ons,
    ]
  }
}

resource "aws_cognito_user_pool_client" "prod_web" {
  name            = "pilot-web-prod"
  user_pool_id    = aws_cognito_user_pool.prod.id
  generate_secret = false # Public SPA client — no client secret
  # Note: generate_secret is ignored on import — existing client may differ; ignore to prevent force-replace

  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_USER_PASSWORD_AUTH", # Required for mobile Expo Go
    "ALLOW_REFRESH_TOKEN_AUTH",
  ]

  # Token TTLs per mvp-arch.md §4.1
  access_token_validity  = 60 # minutes
  id_token_validity      = 60 # minutes
  refresh_token_validity = 30 # days

  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }

  # Prevent force-replace on attributes that differ from manually-created client.
  # generate_secret is ForceNew — ignore so import doesn't trigger destroy+create.
  lifecycle {
    ignore_changes = [
      generate_secret,
      name,
    ]
  }
}

# ─── Lambda: Post-Confirmation Trigger ───────────────────────────────────────
# SIGNUP-GA-1 (ADR-0011): 3-path router that provisions tenant+user rows in RDS
# on Cognito confirmation. Must be in VPC to reach RDS.
#
# Packaging: the build dir is populated by
#   infrastructure/scripts/build-post-confirmation-lambda.sh
# which `pip install -t` Linux manylinux wheels (psycopg2-binary, sqlalchemy,
# sqlmodel, pydantic, pgvector) + copies the handler source + app/models tree.
# Run that script before `terraform plan`/`apply` on this module.
# boto3/botocore are NOT packaged — pre-bundled in the Lambda Python runtime.

data "archive_file" "post_confirmation" {
  type        = "zip"
  output_path = "${path.module}/post_confirmation.zip"
  source_dir  = "${path.module}/build/post_confirmation"
}

resource "aws_lambda_function" "post_confirmation" {
  function_name    = "pilot-${var.environment}-post-confirmation"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.post_confirmation.output_path
  source_code_hash = data.archive_file.post_confirmation.output_base64sha256

  timeout     = 30
  memory_size = 256

  environment {
    variables = {
      ENVIRONMENT          = var.environment
      DB_SECRET_ARN        = aws_secretsmanager_secret.db.arn
      COGNITO_USER_POOL_ID = var.cognito_user_pool_id
    }
  }

  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [var.sg_lambda_id]
  }

  tracing_config {
    mode = "Active" # X-Ray tracing
  }

  tags = {
    Name           = "pilot-${var.environment}-post-confirmation"
    Component      = "auth"
    CostAllocation = "security-monitoring"
    Backup         = "disabled"
  }
}

# Allow Cognito to invoke the Lambda trigger
resource "aws_lambda_permission" "cognito_post_confirmation" {
  statement_id  = "AllowCognitoInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.post_confirmation.function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.prod.arn
}

# ─── Lambda: Post-Authentication Trigger ──────────────────────────────────────
# PLATFORM-SMS-B2 (ADR-0013 / Pathway C): new-device sign-in security alert.
# Fires on every successful Cognito authentication; gates on
# event.request.newDeviceUsed (populated only because device tracking is set to
# "Always remember" — wired manually via CLI, see aws-cognito-prod-setup.md §11).
# On a new-device sign-in it enqueues the existing B1 task
# (send_platform_account_notification_sms) directly to the Redis broker via a
# minimal Celery producer (kombu transport). Must be in VPC to reach RDS + Redis.
#
# Packaging: the build dir is populated by
#   infrastructure/scripts/build-post-authentication-lambda.sh
# which `pip install -t` Linux manylinux wheels (psycopg2-binary, sqlalchemy,
# sqlmodel, pydantic, pgvector, celery) + copies the handler source + app/models
# tree. Run that script before `terraform plan`/`apply` on this module.
# boto3/botocore are NOT packaged — pre-bundled in the Lambda Python runtime.
#
# ⚠️  lambda_config stays in ignore_changes on the user pool (ADR-0011 posture).
#     The Post-Authentication trigger is wired MANUALLY via CLI alongside the
#     existing Post-Confirmation trigger (whole-block overwrite — see
#     aws-cognito-prod-setup.md §11). This aws_lambda_permission grants Cognito
#     invoke rights; the trigger attachment itself is CLI.

data "archive_file" "post_authentication" {
  type        = "zip"
  output_path = "${path.module}/post_authentication.zip"
  source_dir  = "${path.module}/build/post_authentication"
}

resource "aws_lambda_function" "post_authentication" {
  function_name    = "pilot-${var.environment}-post-authentication"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.post_authentication.output_path
  source_code_hash = data.archive_file.post_authentication.output_base64sha256

  timeout     = 30
  memory_size = 256

  environment {
    variables = {
      ENVIRONMENT   = var.environment
      DB_SECRET_ARN = aws_secretsmanager_secret.db.arn
      # The handler fetches this secret at runtime and reads its `broker_url`
      # JSON key (Lambda env vars are plain strings — cannot use the ECS-style
      # `${secret_arn}:json_key::` extraction; same resolution pattern as the
      # DB URL). The `broker_url` key name is verified in compute/main.tf:222.
      REDIS_SECRET_ARN     = aws_secretsmanager_secret.redis.arn
      COGNITO_USER_POOL_ID = var.cognito_user_pool_id
    }
  }

  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [var.sg_lambda_id]
  }

  tracing_config {
    mode = "Active" # X-Ray tracing
  }

  tags = {
    Name           = "pilot-${var.environment}-post-authentication"
    Component      = "auth"
    CostAllocation = "security-monitoring"
    Backup         = "disabled"
  }
}

# Allow Cognito to invoke the Lambda trigger
resource "aws_lambda_permission" "cognito_post_authentication" {
  statement_id  = "AllowCognitoInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.post_authentication.function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.prod.arn
}

# ─── Lambda: Custom Email Sender Trigger ──────────────────────────────────────
# COGNITO-EMAIL-1 (design §C step 4 / §F): Cognito invokes this Lambda instead
# of sending its own auth emails (COGNITO_DEFAULT — 50/day cap, no DKIM/SPF
# control, spam placement). The handler KMS-decrypts the code, renders a branded
# template, and delivers via SendGrid (noreply@pilotfortrades.com).
#
# ⚠️  RETHROW on failure (design §G.4) — the OPPOSITE invariant from the passive
#     hooks above. This Lambda IS the email delivery path: swallowing a failure
#     creates an unrecoverable silent hole. Raise → Cognito surfaces a clean
#     error → CloudWatch Errors alarm fires.
#
# Packaging: the build dir is populated by
#   infrastructure/scripts/build-custom-email-sender-lambda.sh
# which `pip install -t` sendgrid==6.11.0 (+ transitive: python-http-client,
# starkbank-ecdsa) + copies handler.py + templates.py. Self-contained — NO
# app/models bundle (design §B: auth path must not depend on RDS).
# boto3/botocore are NOT packaged — pre-bundled in the Lambda Python runtime.
#
# No VPC config: this Lambda needs only SendGrid (internet), Secrets Manager,
# and KMS — no RDS access. Keeping it out of the VPC avoids the NAT Gateway
# dependency for outbound HTTPS and simplifies the IAM surface.
#
# Dedicated IAM role (secret-management-policy §4 — least privilege): this role
# reads ONLY the sendgrid secret and decrypts ONLY the pilot KMS key. It does
# NOT share the lambda_execution role (which has db + redis + VPC access) —
# the auth email path must not have RDS reach.
#
# ⚠️  lambda_config stays in ignore_changes on the user pool (ADR-0011 posture).
#     The CustomEmailSender trigger + KMSKeyID are wired MANUALLY via CLI
#     alongside the existing PostConfirmation + PostAuthentication triggers
#     (whole-block overwrite — see aws-ops-runbook.md §14.5). This
#     aws_lambda_permission grants Cognito invoke rights; the trigger
#     attachment itself is CLI.

data "archive_file" "custom_email_sender" {
  type        = "zip"
  output_path = "${path.module}/custom_email_sender.zip"
  source_dir  = "${path.module}/build/custom_email_sender"
}

# Dedicated IAM role — least-privilege (secret-management-policy §4).
# Does NOT use the shared lambda_execution role (no db/redis/VPC access).
resource "aws_iam_role" "custom_email_sender" {
  name = "pilot-${var.environment}-custom-email-sender-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = {
    Component      = "auth"
    CostAllocation = "security-monitoring"
  }
}

# Inline policy: secretsmanager:GetSecretValue on the sendgrid secret ONLY;
# kms:Decrypt on the pilot KMS key ONLY; CloudWatch Logs basic execution.
resource "aws_iam_role_policy" "custom_email_sender" {
  name = "pilot-${var.environment}-custom-email-sender-policy"
  role = aws_iam_role.custom_email_sender.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SendGridSecretRead"
        Effect = "Allow"
        Action = ["secretsmanager:GetSecretValue"]
        # Least-privilege: ONLY the sendgrid secret (secret-management-policy §4).
        # Do NOT wildcard; do NOT add other secret ARNs.
        Resource = [aws_secretsmanager_secret.sendgrid.arn]
      },
      {
        Sid    = "KMSDecrypt"
        Effect = "Allow"
        Action = ["kms:Decrypt"]
        # ONLY the pilot CMK — Cognito encrypts request.code with this key.
        Resource = [aws_kms_key.pilot.arn]
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = ["arn:aws:logs:${var.aws_region}:${var.account_id}:log-group:/aws/lambda/pilot-${var.environment}-custom-email-sender:*"]
      },
    ]
  })
}

resource "aws_lambda_function" "custom_email_sender" {
  function_name    = "pilot-${var.environment}-custom-email-sender"
  role             = aws_iam_role.custom_email_sender.arn
  handler          = "handler.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.custom_email_sender.output_path
  source_code_hash = data.archive_file.custom_email_sender.output_base64sha256

  timeout = 30
  # 512 MB — the AWS Encryption SDK + cryptography library has a larger memory
  # footprint than the self-contained sendgrid-only package originally planned.
  # 256 MB caused cold-start OOM risk with the encryption SDK imports.
  memory_size = 512

  environment {
    variables = {
      # The handler resolves the SendGrid key: env SENDGRID_API_KEY (local/tests)
      # → else fetch from Secrets Manager via this ARN (JSON key SENDGRID_API_KEY).
      SENDGRID_SECRET_ARN = aws_secretsmanager_secret.sendgrid.arn
      # KMS key ARN — Cognito encrypts the auth code with this key via the
      # AWS Encryption SDK; the handler builds a strict KMS keyring from this ARN.
      KMS_KEY_ARN = aws_kms_key.pilot.arn
    }
  }

  # No VPC config — this Lambda needs no RDS access (design §B self-contained).
  # Outbound HTTPS to SendGrid uses the Lambda internet path (no NAT needed).

  tracing_config {
    mode = "Active" # X-Ray tracing
  }

  tags = {
    Name           = "pilot-${var.environment}-custom-email-sender"
    Component      = "auth"
    CostAllocation = "security-monitoring"
    Backup         = "disabled"
  }
}

# Allow Cognito to invoke the Lambda trigger
resource "aws_lambda_permission" "cognito_custom_email_sender" {
  statement_id  = "AllowCognitoInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.custom_email_sender.function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.prod.arn
}

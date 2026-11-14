# ─── ECR Repositories ─────────────────────────────────────────────────────────

locals {
  ecr_repos = ["pilot/api", "pilot/worker", "pilot/beat", "pilot/web"]

  # Single source for the speech-to-text model: preloaded on the GPU
  # (gpu_userdata.sh) and requested by the API/worker (WHISPER_MODEL), so the
  # model the app asks for is always the one the GPU serves.
  whisper_model = "Systran/faster-whisper-large-v3"
}

resource "aws_ecr_repository" "repos" {
  for_each = toset(local.ecr_repos)

  name                 = each.key
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true # ECR basic scan on push (CVE findings are not gated in CI)
  }

  tags = {
    Name           = each.key
    Component      = "api-backend"
    CostAllocation = "web-infrastructure"
    Backup         = "disabled"
  }
}

# Lifecycle policy: keep last 10 tagged images; delete untagged after 1 day
resource "aws_ecr_lifecycle_policy" "repos" {
  for_each   = toset(local.ecr_repos)
  repository = each.key

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Delete untagged images after 1 day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = { type = "expire" }
      },
      {
        rulePriority = 2
        description  = "Keep last 10 tagged images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v", "sha-", "latest"]
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = { type = "expire" }
      }
    ]
  })
}

# ─── ECS Cluster ──────────────────────────────────────────────────────────────

resource "aws_ecs_cluster" "production" {
  name = "pilot-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name           = "pilot-${var.environment}-cluster"
    Component      = "api-backend"
    CostAllocation = "web-infrastructure"
    Backup         = "disabled"
  }
}

resource "aws_ecs_cluster_capacity_providers" "production" {
  cluster_name       = aws_ecs_cluster.production.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
  }
}

# ─── ALB: Application Load Balancer ───────────────────────────────────────────

resource "aws_lb" "api" {
  name               = "pilot-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.sg_alb_id]
  subnets            = var.public_subnet_ids

  enable_deletion_protection = false # HIBERNATE-1: toggled off for teardown; restart restores true

  tags = {
    Name           = "pilot-${var.environment}-alb"
    Component      = "networking"
    CostAllocation = "networking"
    Backup         = "disabled"
  }
}

# Blue target group (initial — receives 100% traffic at launch)
resource "aws_lb_target_group" "api_blue" {
  name        = "pilot-${var.environment}-api-blue"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip" # Required for Fargate awsvpc networking

  health_check {
    enabled             = true
    path                = "/api/v1/health/celery"
    port                = "traffic-port"
    healthy_threshold   = 3
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    matcher             = "200"
  }

  tags = {
    Name           = "pilot-${var.environment}-api-blue"
    Component      = "networking"
    CostAllocation = "networking"
  }
}

# Green target group (provisioned for a future blue-green deployment; not used —
# deploys are ECS rolling with circuit-breaker rollback)
resource "aws_lb_target_group" "api_green" {
  name        = "pilot-${var.environment}-api-green"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    path                = "/api/v1/health/celery"
    port                = "traffic-port"
    healthy_threshold   = 3
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    matcher             = "200"
  }

  tags = {
    Name           = "pilot-${var.environment}-api-green"
    Component      = "networking"
    CostAllocation = "networking"
  }
}

# HTTPS listener — requires validated ACM cert; gated by var.acm_cert_validated
# Set acm_cert_validated = true after Phase 5 GoDaddy NS cutover + cert validates
resource "aws_lb_listener" "https" {
  count = var.acm_cert_validated ? 1 : 0

  load_balancer_arn = aws_lb.api.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.acm_certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api_blue.arn
  }
}

# HTTP → HTTPS redirect
resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# ─── ECS Task Definitions ─────────────────────────────────────────────────────

# Shared log configuration helper
locals {
  log_config_api = {
    logDriver = "awslogs"
    options = {
      "awslogs-group"         = "/ecs/pilot-api"
      "awslogs-region"        = var.aws_region
      "awslogs-stream-prefix" = "ecs"
    }
  }
  log_config_worker = {
    logDriver = "awslogs"
    options = {
      "awslogs-group"         = "/ecs/pilot-celery-worker"
      "awslogs-region"        = var.aws_region
      "awslogs-stream-prefix" = "ecs"
    }
  }
  log_config_beat = {
    logDriver = "awslogs"
    options = {
      "awslogs-group"         = "/ecs/pilot-celery-beat"
      "awslogs-region"        = var.aws_region
      "awslogs-stream-prefix" = "ecs"
    }
  }

  # Secrets injected at runtime from Secrets Manager — never baked into image
  common_secrets = [
    { name = "DATABASE_URL", valueFrom = "${var.secret_db_arn}:url::" },
    { name = "CELERY_BROKER_URL", valueFrom = "${var.secret_redis_arn}:broker_url::" },
    { name = "CELERY_RESULT_BACKEND", valueFrom = "${var.secret_redis_arn}:result_url::" },
    { name = "REDIS_URL", valueFrom = "${var.secret_redis_arn}:rate_url::" },
    { name = "SENDGRID_API_KEY", valueFrom = "${var.secret_sendgrid_arn}:api_key::" },
    { name = "TELNYX_API_KEY", valueFrom = "${var.secret_telnyx_arn}:api_key::" },
    # TELNYX-INT-1 (2026-08-09): complete Telnyx env injection — previously only API_KEY was mapped,
    # leaving prod silently on SMS_CARRIER=mock (config default) with no webhook signature verification.
    { name = "TELNYX_PUBLIC_KEY", valueFrom = "${var.secret_telnyx_arn}:public_key::" },
    { name = "TELNYX_MESSAGING_PROFILE_ID", valueFrom = "${var.secret_telnyx_arn}:messaging_profile_id::" },
    { name = "PILOT_PLATFORM_SMS_NUMBER", valueFrom = "${var.secret_telnyx_arn}:platform_sms_number::" },
    { name = "STRIPE_SECRET_KEY", valueFrom = "${var.secret_stripe_arn}:secret_key::" },
    { name = "STRIPE_PUBLISHABLE_KEY", valueFrom = "${var.secret_stripe_arn}:publishable_key::" },
    { name = "STRIPE_WEBHOOK_SECRET", valueFrom = "${var.secret_stripe_arn}:webhook_secret::" },
    { name = "STRIPE_CONNECT_PLATFORM_KEY", valueFrom = "${var.secret_stripe_arn}:connect_platform_key::" },
    { name = "STRIPE_CONNECT_WEBHOOK_SECRET", valueFrom = "${var.secret_stripe_arn}:connect_webhook_secret::" },
    { name = "QUICKBOOKS_CLIENT_ID", valueFrom = "${var.secret_quickbooks_arn}:client_id::" },
    { name = "QUICKBOOKS_CLIENT_SECRET", valueFrom = "${var.secret_quickbooks_arn}:client_secret::" },
    { name = "QUICKBOOKS_WEBHOOK_VERIFIER_TOKEN", valueFrom = "${var.secret_quickbooks_arn}:webhook_verifier_token::" },
    { name = "ENCRYPTION_KEY", valueFrom = "${var.secret_encryption_arn}:fernet_key::" },
    { name = "COGNITO_USER_POOL_ID", valueFrom = "${var.secret_cognito_arn}:user_pool_id::" },
    { name = "GOOGLE_MAPS_API_KEY", valueFrom = "${var.secret_google_maps_arn}:api_key::" },
    { name = "CLOUDFLARE_TURNSTILE_SECRET_KEY", valueFrom = "${var.secret_turnstile_arn}:secret_key::" },
  ]
}

# FastAPI API Task Definition
resource "aws_ecs_task_definition" "api" {
  family                   = "pilot-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256  # 0.25 vCPU
  memory                   = 1024 # MB — bumped from 512 (2026-07-06: two uvicorn workers × ~200 MB baseline consumed ~400 MB at idle in 512 MB leaving only ~110 MB headroom)
  execution_role_arn       = var.ecs_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn

  container_definitions = jsonencode([{
    name      = "api"
    image     = "${aws_ecr_repository.repos["pilot/api"].repository_url}:latest"
    essential = true
    command   = ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

    portMappings = [{
      containerPort = 8000
      hostPort      = 8000
      protocol      = "tcp"
    }]

    environment = [
      { name = "ENVIRONMENT", value = "production" },
      { name = "TEST_ENDPOINT_ENABLED", value = "false" },
      { name = "QUICKBOOKS_ENVIRONMENT", value = "production" },
      { name = "QUICKBOOKS_REDIRECT_URI", value = "https://api.${var.domain_name}/api/v1/integrations/quickbooks/callback" },
      { name = "API_BASE_URL", value = "https://api.${var.domain_name}" },
      { name = "SENDGRID_FROM_EMAIL", value = "noreply@${var.domain_name}" },
      { name = "COGNITO_REGION", value = var.aws_region },
      { name = "AWS_DEFAULT_REGION", value = var.aws_region },
      { name = "WHISPER_MODEL", value = local.whisper_model },
      # TELNYX-INT-1 (2026-08-09): prod must use the real Telnyx carrier, not the mock default.
      # §19.6 addendum (2026-08-10): every mode-toggle env var must be explicit in prod task defs.
      # TELNYX_10DLC_MOCK=false is set explicitly — relying on the code default (also false)
      # left a silent-failure vector when a baked .env reached prod (see §19.7).
      { name = "SMS_CARRIER", value = "telnyx" },
      { name = "TELNYX_10DLC_MOCK", value = "false" },
      # SIGNUP-GA-B1: Trust ALB's X-Forwarded-Proto so uvicorn builds https://
      # redirect URLs. Without this, 307 redirects from FastAPI use http://
      # (uvicorn's ProxyHeadersMiddleware only trusts forwarded_allow_ips,
      # default 127.0.0.1; behind the ALB the peer is a VPC IP). Safe because
      # the ALB is the sole ingress and sg-web/sg-alb restrict access.
      { name = "FORWARDED_ALLOW_IPS", value = "*" },
      # C-B16-OPS: tenant-sites base domain — backend builds https://{slug}.{domain} URLs
      { name = "TENANT_SITES_BASE_DOMAIN", value = "p4tsites.com" },
      # TEST-UPLIFT-1A: Maps drive-time Redis cache — OFF by default (config.py),
      # must be explicitly enabled in prod. Protects ~$77/mo variable Maps spend.
      { name = "MAP_CACHE_ENABLED", value = "true" },
      { name = "MAP_CACHE_TTL_SECONDS", value = "86400" },
    ]

    secrets = local.common_secrets

    logConfiguration = local.log_config_api

    # X-Ray ADOT sidecar — 5% sampling in production
    # Uncomment to enable distributed tracing
    # dependsOn = [{ containerName = "xray-daemon", condition = "START" }]
  }])

  tags = {
    Component      = "api-backend"
    Service        = "fastapi-api"
    CostAllocation = "web-infrastructure"
    Backup         = "disabled"
  }
}

# Celery Worker Task Definition
resource "aws_ecs_task_definition" "worker" {
  family                   = "pilot-celery-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = var.ecs_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn

  container_definitions = jsonencode([{
    name      = "worker"
    image     = "${aws_ecr_repository.repos["pilot/worker"].repository_url}:latest"
    essential = true
    command   = ["celery", "-A", "core.celery_app", "worker", "--loglevel=info", "--concurrency=2"]

    environment = [
      { name = "ENVIRONMENT", value = "production" },
      { name = "TEST_ENDPOINT_ENABLED", value = "false" },
      { name = "QUICKBOOKS_ENVIRONMENT", value = "production" },
      { name = "API_BASE_URL", value = "https://api.${var.domain_name}" },
      { name = "SENDGRID_FROM_EMAIL", value = "noreply@${var.domain_name}" },
      { name = "COGNITO_REGION", value = var.aws_region },
      { name = "AWS_DEFAULT_REGION", value = var.aws_region },
      { name = "WHISPER_MODEL", value = local.whisper_model },
      # TELNYX-INT-1 (2026-08-09): worker sends SMS via notification_worker → get_sms_carrier().
      # §19.6 addendum (2026-08-10): explicit mode-toggle — this is the service that booted in
      # mock mode on 2026-08-10 because the flag was absent and fell through to a baked .env.
      { name = "SMS_CARRIER", value = "telnyx" },
      { name = "TELNYX_10DLC_MOCK", value = "false" },
      # C-B16-OPS: tenant-sites base domain — worker builds site URLs in the
      # C-B16 requirements email + profile hook paths
      { name = "TENANT_SITES_BASE_DOMAIN", value = "p4tsites.com" },
      # TEST-UPLIFT-1A: Maps drive-time Redis cache — parity with api container.
      { name = "MAP_CACHE_ENABLED", value = "true" },
      { name = "MAP_CACHE_TTL_SECONDS", value = "86400" },
    ]

    secrets = local.common_secrets

    logConfiguration = local.log_config_worker
  }])

  tags = {
    Component      = "api-backend"
    Service        = "celery-worker"
    CostAllocation = "web-infrastructure"
    Backup         = "disabled"
  }
}

# Celery Beat Task Definition (single instance — no scaling)
resource "aws_ecs_task_definition" "beat" {
  family                   = "pilot-celery-beat"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512 # Fargate minimum for 256 CPU is 512 MB
  execution_role_arn       = var.ecs_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn

  container_definitions = jsonencode([{
    name      = "beat"
    image     = "${aws_ecr_repository.repos["pilot/beat"].repository_url}:latest"
    essential = true
    command   = ["celery", "-A", "core.celery_app", "beat", "--loglevel=info"]

    environment = [
      { name = "ENVIRONMENT", value = "production" },
      { name = "TEST_ENDPOINT_ENABLED", value = "false" },
      { name = "QUICKBOOKS_ENVIRONMENT", value = "production" },
      { name = "API_BASE_URL", value = "https://api.${var.domain_name}" },
      { name = "SENDGRID_FROM_EMAIL", value = "noreply@${var.domain_name}" },
      { name = "COGNITO_REGION", value = var.aws_region },
      { name = "AWS_DEFAULT_REGION", value = var.aws_region },
      # TELNYX-INT-1 (2026-08-09): beat doesn't send SMS directly, but consistency with the
      # shared carrier config avoids drift if a beat task ever invokes the carrier factory.
      # §19.6 addendum (2026-08-10): explicit mode-toggle parity with api/worker.
      { name = "SMS_CARRIER", value = "telnyx" },
      { name = "TELNYX_10DLC_MOCK", value = "false" },
    ]

    secrets = local.common_secrets

    logConfiguration = local.log_config_beat
  }])

  tags = {
    Component      = "api-backend"
    Service        = "celery-beat"
    CostAllocation = "web-infrastructure"
    Backup         = "disabled"
  }
}

# ─── ECS Services ─────────────────────────────────────────────────────────────
# All ECS services gated by var.ecr_images_available:
# - Require ECR images (docker push Phase 6)
# - api service requires HTTPS ALB listener (needs validated cert Phase 5)
# Set ecr_images_available = true after Phase 6 first docker push.

resource "aws_ecs_service" "api" {
  count           = var.ecr_images_available ? 1 : 0
  name            = "pilot-api"
  cluster         = aws_ecs_cluster.production.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.ecs_api_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.sg_ecs_api_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api_blue.arn
    container_name   = "api"
    container_port   = 8000
  }

  # ECS rolling deployment — Phase 1 MVP
  # Upgrade to CODE_DEPLOY (blue/green with traffic shifting per blue-green-constraints.md)
  # in Phase 2 after first successful rolling deploy is confirmed
  deployment_controller {
    type = "ECS"
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true # Auto-rollback if deployment fails health checks
  }

  # As built: ECS rolling deploy (100% min healthy / 200% max) with the circuit
  # breaker. The blue-green and canary phases in blue-green-constraints.md were
  # designed but never enabled.
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200

  health_check_grace_period_seconds = 90

  # Depends on http_redirect (always exists); https listener gated by acm_cert_validated
  depends_on = [aws_lb_listener.http_redirect, aws_lb.api]

  tags = {
    Component      = "api-backend"
    Service        = "fastapi-api"
    CostAllocation = "web-infrastructure"
    Backup         = "disabled"
  }

  lifecycle {
    ignore_changes = [task_definition] # CI/CD manages task definition updates
  }
}

resource "aws_ecs_service" "worker" {
  count           = var.ecr_images_available ? 1 : 0
  name            = "pilot-celery-worker"
  cluster         = aws_ecs_cluster.production.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = var.ecs_worker_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.sg_ecs_api_id]
    assign_public_ip = false
  }

  deployment_controller {
    type = "ECS"
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200

  tags = {
    Component      = "api-backend"
    Service        = "celery-worker"
    CostAllocation = "web-infrastructure"
    Backup         = "disabled"
  }

  lifecycle {
    ignore_changes = [task_definition]
  }
}

resource "aws_ecs_service" "beat" {
  count           = var.ecr_images_available ? 1 : 0
  name            = "pilot-celery-beat"
  cluster         = aws_ecs_cluster.production.id
  task_definition = aws_ecs_task_definition.beat.arn
  desired_count   = 1 # Exactly 1 — Beat must never run as multiple instances
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.sg_ecs_api_id]
    assign_public_ip = false
  }

  deployment_controller {
    type = "ECS"
  }

  # Beat: replace old task before starting new one to prevent dual-beat split-brain
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100

  tags = {
    Component      = "api-backend"
    Service        = "celery-beat"
    CostAllocation = "web-infrastructure"
    Backup         = "disabled"
  }

  lifecycle {
    ignore_changes = [task_definition]
  }
}

# ─── EC2 GPU Instance (g4dn.xlarge) ───────────────────────────────────────────
# Gated by var.gpu_quota_approved — g4dn instances require a vCPU service quota increase.
# Request at: AWS Console → Service Quotas → EC2 → "Running On-Demand G and VT instances"
# After approval (typically 1-3 business days), set gpu_quota_approved = true and re-apply.

resource "aws_instance" "gpu" {
  count                  = var.gpu_quota_approved ? 1 : 0
  ami                    = var.gpu_ami_id
  instance_type          = "g4dn.xlarge"             # 4 vCPU, 16GB RAM, NVIDIA T4 16GB VRAM
  subnet_id              = var.private_subnet_ids[0] # us-east-1a private subnet
  vpc_security_group_ids = [var.sg_gpu_id]
  key_name               = var.bastion_key_name
  iam_instance_profile   = aws_iam_instance_profile.gpu.name

  # Root volume — 50GB for OS + Docker layers
  root_block_device {
    volume_type           = "gp3"
    volume_size           = 50
    encrypted             = true
    kms_key_id            = var.kms_key_arn
    delete_on_termination = true
  }

  # Model storage — 20GB for Ollama (~4.7GB) + Whisper (~1.5GB) + headroom
  ebs_block_device {
    device_name           = "/dev/xvdb"
    volume_type           = "gp3"
    volume_size           = 20
    encrypted             = true
    kms_key_id            = var.kms_key_arn
    delete_on_termination = false # Preserve models if instance is replaced
  }

  user_data = base64encode(templatefile("${path.module}/gpu_userdata.sh", {
    aws_region    = var.aws_region
    whisper_model = local.whisper_model
  }))

  tags = {
    Name               = "pilot-${var.environment}-gpu"
    Component          = "ai-pipeline"
    Service            = "whisper-ollama"
    CostAllocation     = "ai-pipeline"
    DataClassification = "internal"
    Backup             = "enabled"
  }

  lifecycle {
    # GPU instances take 15+ minutes to start with model downloads;
    # only replace if instance_type or AMI changes, not on userdata changes
    ignore_changes = [user_data]
  }
}

resource "aws_iam_role" "gpu" {
  name = "pilot-${var.environment}-gpu-instance-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "gpu_ssm" {
  role       = aws_iam_role.gpu.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "gpu_cloudwatch" {
  role       = aws_iam_role.gpu.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

resource "aws_iam_instance_profile" "gpu" {
  name = "pilot-${var.environment}-gpu-profile"
  role = aws_iam_role.gpu.name
}

# ─── CloudFront Distribution (Marketing Site) ─────────────────────────────────

# CloudFront Function — rewrites clean URL paths to their .html equivalents for S3 static export.
# Next.js static export (output: "export") generates FLAT .html files at the bucket root:
#   /features  →  features.html  (S3 key: features.html)
#   /pricing   →  pricing.html   (S3 key: pricing.html)
#   /about     →  about.html     (S3 key: about.html)
# NOT /features/index.html — there are NO index.html files in subdirectories.
# S3 REST API (used by OAC) returns 403 for /features because the key is features.html.
# This function rewrites the URI before S3 sees the request:
#   /           → /index.html        (root — default_root_object handles this but be explicit)
#   /features   → /features.html
#   /features/  → /features.html     (strip trailing slash)
# Paths already ending in a file extension pass through unchanged (static assets, RSC payloads).
resource "aws_cloudfront_function" "spa_rewrite" {
  name    = "pilot-${var.environment}-spa-index-rewrite"
  runtime = "cloudfront-js-2.0"
  comment = "Rewrite clean URLs to .html for Next.js flat static export on S3"
  publish = true

  code = <<-EOF
    async function handler(event) {
      const request = event.request;
      let uri = request.uri;

      // Pass through paths with a file extension (static assets, _next/static, .txt RSC, etc.)
      if (/\.[a-zA-Z0-9]+$/.test(uri)) {
        return request;
      }

      // Strip trailing slash (except root /)
      if (uri !== '/' && uri.endsWith('/')) {
        uri = uri.slice(0, -1);
      }

      // Root → /index.html
      if (uri === '/') {
        request.uri = '/index.html';
        return request;
      }

      // All other clean paths → /<path>.html
      // e.g. /features → /features.html, /legal/terms → /legal/terms.html
      request.uri = uri + '.html';
      return request;
    }
  EOF
}

resource "aws_cloudfront_origin_access_control" "marketing" {
  name                              = "pilot-${var.environment}-marketing-oac"
  description                       = "OAC for pilot marketing S3 bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# CloudFront requires a validated ACM cert for custom aliases.
# When acm_cert_validated = false, uses CloudFront default cert with no aliases.
# After Phase 5 GoDaddy NS cutover + cert validates: set acm_cert_validated = true and re-apply.
resource "aws_cloudfront_distribution" "marketing" {
  origin {
    # S3 regional domain — required for OAC (not the website endpoint)
    domain_name              = "pilot-${var.environment}-marketing.s3.us-east-1.amazonaws.com"
    origin_id                = "S3-pilot-${var.environment}-marketing"
    origin_access_control_id = aws_cloudfront_origin_access_control.marketing.id
  }

  aliases = var.acm_cert_validated ? [var.domain_name, "www.${var.domain_name}"] : []

  enabled             = true
  is_ipv6_enabled     = true
  comment             = "Pilot for Trades marketing site CDN"
  default_root_object = "index.html"
  price_class         = "PriceClass_100" # US + Europe only — saves ~30%

  # Next.js static export: S3 REST API returns 403 for directory paths (e.g. /features)
  # because only /features/index.html exists as an S3 key. CloudFront rewrites to /index.html.
  # error_caching_min_ttl = 0 prevents CloudFront from caching the error response for the
  # default 300 seconds — without this, every direct hit to /features returns the home page
  # for 5 minutes, causing the intermittent "stays on home page" symptom.
  custom_error_response {
    error_code            = 403
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }

  custom_error_response {
    error_code            = 404
    response_code         = 404
    response_page_path    = "/404.html"
    error_caching_min_ttl = 0
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-pilot-${var.environment}-marketing"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }

    # Cache static assets aggressively; HTML uses no-cache (set via S3 metadata)
    min_ttl     = 0
    default_ttl = 86400    # 1 day
    max_ttl     = 31536000 # 1 year

    # Rewrite /features → /features/index.html before the request hits S3.
    # Without this, S3 REST API (OAC) returns 403 for all directory paths
    # because only /features/index.html exists as an S3 key, not /features.
    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.spa_rewrite.arn
    }
  }

  viewer_certificate {
    acm_certificate_arn            = var.acm_cert_validated ? var.acm_certificate_arn : null
    cloudfront_default_certificate = var.acm_cert_validated ? false : true
    ssl_support_method             = var.acm_cert_validated ? "sni-only" : null
    minimum_protocol_version       = var.acm_cert_validated ? "TLSv1.2_2021" : "TLSv1"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  tags = {
    Name           = "pilot-${var.environment}-marketing-cdn"
    Component      = "marketing-site"
    CostAllocation = "marketing"
    Backup         = "disabled"
  }
}

# ─── ECS: Web Dashboard (pilot-web) ───────────────────────────────────────────
# Replaces AWS App Runner (sunset April 30, 2026) as the 4th ECS Fargate service.
# Shares the existing pilot-production cluster + ALB; host-based routing via
# "Host: app.pilotfortrades.com" listener rule at priority 10.

# Security group: allows ALB → Next.js port 3000
resource "aws_security_group" "sg_web" {
  name        = "pilot-${var.environment}-sg-web"
  description = "pilot-web ECS service - allows ALB to reach Next.js on port 3000"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Next.js from ALB"
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [var.sg_alb_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name      = "pilot-${var.environment}-sg-web"
    Component = "web-dashboard"
    Service   = "web-dashboard"
  }
}

# ALB target group for Next.js on port 3000
resource "aws_lb_target_group" "web" {
  name        = "pilot-${var.environment}-web"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip" # Required for Fargate awsvpc networking

  health_check {
    enabled             = true
    path                = "/api/health"
    protocol            = "HTTP"
    port                = "traffic-port"
    healthy_threshold   = 3
    unhealthy_threshold = 3
    timeout             = 10
    interval            = 30
    matcher             = "200"
  }

  tags = {
    Name      = "pilot-${var.environment}-web-tg"
    Component = "web-dashboard"
    Service   = "web-dashboard"
  }
}

# ALB listener rule: Host: app.pilotfortrades.com → web target group
# Priority 10 — evaluated before any catch-all API rule
resource "aws_lb_listener_rule" "web" {
  listener_arn = aws_lb_listener.https[0].arn
  priority     = 10

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web.arn
  }

  condition {
    host_header {
      values = ["app.${var.domain_name}"]
    }
  }

  tags = {
    Name      = "pilot-${var.environment}-web-listener-rule"
    Component = "web-dashboard"
  }
}

# C-B16-OPS (ADR-0014): tenant-sites wildcard → pilot-web TG (SNI on shared ALB)
# Adds the p4tsites.com ACM cert as a second listener certificate (SNI).
# The ALB presents this cert when the SNI hostname matches *.p4tsites.com.
resource "aws_lb_listener_certificate" "p4tsites" {
  listener_arn    = aws_lb_listener.https[0].arn
  certificate_arn = var.p4tsites_certificate_arn
}

# C-B16-OPS (ADR-0014): host-header rule for *.p4tsites.com → pilot-web TG
# Priority 15 — after web (10), before any catch-all API rule.
# Do NOT add an apex/www ALB rule — the apex redirect lives at the Cloudflare
# edge (§G-11, ADR-0014). Only the wildcard host rule burns an ALB rule slot.
resource "aws_lb_listener_rule" "tenant_sites" {
  listener_arn = aws_lb_listener.https[0].arn
  priority     = 15

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web.arn
  }

  condition {
    host_header {
      values = ["*.p4tsites.com"]
    }
  }

  tags = {
    Name      = "pilot-${var.environment}-tenant-sites-listener-rule"
    Component = "tenant-sites"
  }
}

# CloudWatch log group for pilot-web
resource "aws_cloudwatch_log_group" "web" {
  name              = "/ecs/pilot-${var.environment}-web"
  retention_in_days = 30

  tags = {
    Name           = "/ecs/pilot-${var.environment}-web"
    Component      = "web-dashboard"
    Service        = "web-dashboard"
    CostAllocation = "web-infrastructure"
  }
}

# ECS Task Definition for Next.js web dashboard (0.5 vCPU / 1024 MB)
resource "aws_ecs_task_definition" "web" {
  family                   = "pilot-${var.environment}-web"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"  # 0.5 vCPU
  memory                   = "1024" # 1024 MB

  execution_role_arn = var.ecs_execution_role_arn
  task_role_arn      = var.ecs_task_role_arn

  container_definitions = jsonencode([{
    name  = "web"
    image = "${aws_ecr_repository.repos["pilot/web"].repository_url}:latest"
    portMappings = [{
      containerPort = 3000
      protocol      = "tcp"
    }]
    environment = [
      { name = "NEXT_PUBLIC_API_URL", value = "https://api.${var.domain_name}" },
      { name = "NEXT_PUBLIC_COGNITO_REGION", value = var.aws_region },
      { name = "NEXT_PUBLIC_COGNITO_USER_POOL_ID", value = var.cognito_user_pool_id },
      { name = "NEXT_PUBLIC_COGNITO_APP_CLIENT_ID", value = var.cognito_app_client_id },
      { name = "NEXT_PUBLIC_USE_MOCK_AUTH", value = "false" },
      { name = "NEXT_PUBLIC_USE_MSW_MOCKS", value = "false" },
      { name = "NODE_ENV", value = "production" },
      # C-B16-OPS / TS-BUG-1: tenant-sites domain — consumed by src/proxy.ts host-rewrite.
      # TS-BUG-1: proxy.ts reads the Host header directly + tries multiple candidate
      # domains (p4tsites.com, localhost) as fallback, so this env var is belt-and-suspenders.
      # NEXT_PUBLIC_* is inlined at image build time (Dockerfile build-arg); this task-def
      # value is for runtime reference only.
      { name = "NEXT_PUBLIC_TENANT_SITES_DOMAIN", value = "p4tsites.com" },
      # TS-BUG-1: non-public runtime env var — read at runtime by proxy.ts (not inlined
      # at build time). Belt-and-suspenders alongside the multi-domain fallback.
      { name = "TENANT_SITES_DOMAIN", value = "p4tsites.com" }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/ecs/pilot-${var.environment}-web"
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
    # Container-level health check removed — rely on ALB target group health check only.
    # The ALB HTTP check (GET /api/health → 200) is the authoritative health signal.
    # curl/wget inside Alpine Fargate containers fail to connect to localhost:3000
    # regardless of whether curl is installed, likely due to Fargate network namespace
    # isolation affecting loopback. The ALB external check works correctly.
  }])

  tags = {
    Name           = "pilot-${var.environment}-web"
    Component      = "web-dashboard"
    Service        = "web-dashboard"
    CostAllocation = "web-infrastructure"
    Backup         = "disabled"
  }
}

# ECS Service for pilot-web (1 Fargate task, private subnets, ALB-attached)
resource "aws_ecs_service" "web" {
  name            = "pilot-web"
  cluster         = aws_ecs_cluster.production.id
  task_definition = aws_ecs_task_definition.web.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.sg_web.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.web.arn
    container_name   = "web"
    container_port   = 3000
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  health_check_grace_period_seconds  = 90

  # Listener rule must exist before service registers with target group
  depends_on = [aws_lb_listener_rule.web]

  tags = {
    Name           = "pilot-${var.environment}-web-service"
    Component      = "web-dashboard"
    Service        = "web-dashboard"
    CostAllocation = "web-infrastructure"
    Backup         = "disabled"
  }

  lifecycle {
    ignore_changes = [task_definition] # CI/CD manages task definition updates
  }
}

# ─── Route 53 DNS Records ─────────────────────────────────────────────────────
# zone_id is passed as a variable from module.security (Route 53 zone created there)

# pilotfortrades.com → CloudFront (marketing site)
resource "aws_route53_record" "marketing_apex" {
  zone_id = var.route53_zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.marketing.domain_name
    zone_id                = aws_cloudfront_distribution.marketing.hosted_zone_id
    evaluate_target_health = false
  }
}

# www.pilotfortrades.com → CloudFront
resource "aws_route53_record" "marketing_www" {
  zone_id = var.route53_zone_id
  name    = "www.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.marketing.domain_name
    zone_id                = aws_cloudfront_distribution.marketing.hosted_zone_id
    evaluate_target_health = false
  }
}

# api.pilotfortrades.com → ALB
resource "aws_route53_record" "api" {
  zone_id = var.route53_zone_id
  name    = "api.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_lb.api.dns_name
    zone_id                = aws_lb.api.zone_id
    evaluate_target_health = true
  }
}

# app.pilotfortrades.com → ALB (A alias, same ALB as api.pilotfortrades.com)
# Host-based routing: ALB listener rule (priority 10) routes app.* → pilot-web target group
resource "aws_route53_record" "app" {
  zone_id = var.route53_zone_id
  name    = "app.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_lb.api.dns_name
    zone_id                = aws_lb.api.zone_id
    evaluate_target_health = true
  }
}

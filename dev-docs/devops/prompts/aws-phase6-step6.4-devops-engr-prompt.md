# AWS Deployment — Phase 6 Step 6.4: ECS Fargate Web Service (`pilot-web`)

**Mode**: `pilot-devops-engineer`  
**Phase**: 6 Step 6.4 — Web Dashboard ECS Fargate Service  
**Created**: 2026-07-03  
**Status doc**: [`dev-docs/devops/aws-deployment-status.md`](../aws-deployment-status.md)  
**Deployment plan ref**: [`dev-docs/devops/aws-deployment-plan-v1.md §5 Phase 6 Step 6.4`](../aws-deployment-plan-v1.md)  
**As-built ref**: [`dev-docs/devops/aws-infrastructure-as-built.md §3`](../aws-infrastructure-as-built.md)  
**Platform**: AWS · `us-east-1` · HotRMC account `000000000000`

---

## ⚠️ MANDATORY STOP — Read These Before Starting

1. [`dev-docs/devops/aws-deployment-status.md`](../aws-deployment-status.md) — Phase 6 Step 6.4 section for current status
2. [`dev-docs/devops/aws-infrastructure-as-built.md §3`](../aws-infrastructure-as-built.md) — ECS Fargate web dashboard spec
3. [`infrastructure/terraform/modules/compute/main.tf`](../../../infrastructure/terraform/modules/compute/main.tf) — current Terraform compute module
4. [`infrastructure/terraform/modules/security/main.tf`](../../../infrastructure/terraform/modules/security/main.tf) — IAM roles to clean up
5. [`infrastructure/scripts/generate-infra-state.sh`](../../../infrastructure/scripts/generate-infra-state.sh) — script to update
6. [`infrastructure/scripts/.infra-state.env.example`](../../../infrastructure/scripts/.infra-state.env.example) — example state file format

---

## Background

AWS App Runner was sunset April 30, 2026. No new App Runner services can be created on any AWS account. The HotRMC account confirmed this during Phase 6 Step 6.4 — the web dashboard hosting platform must change.

**The `pilot/web:latest` ECR image is ready** — confirmed working locally (`GET /api/health → HTTP 200`).

**Decision**: `pilot-web` runs as the 4th ECS Fargate service on the existing `pilot-production` cluster. The existing ALB is shared via a `Host: app.pilotfortrades.com` listener rule — zero marginal ALB cost.

---

## Current State

| Item | Value | Status |
|---|---|---|
| AWS Account | HotRMC `000000000000` | ✅ Active |
| ECS Cluster | `pilot-production` | ✅ Running |
| ECS backend services | `pilot-api` (2), `pilot-celery-worker` (2), `pilot-celery-beat` (1) | ✅ ACTIVE |
| ECR `pilot/web` | `000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/web:latest` | ✅ Image confirmed working |
| ALB | `pilot-production-alb` | ✅ Running |
| `app.pilotfortrades.com` DNS | CNAME → (old App Runner URL — invalid) | ⚠️ Needs update |
| `pilot-production-app-runner-role` IAM | Exists but unused | 🗑️ Remove |
| `pilot-web` ECS service | Does not exist | ⬜ Create |
| App Runner service | Does not exist (sunset April 30, 2026) | N/A |

---

## Pre-Work: Verify Starting State

```bash
# 1. Correct AWS account
aws sts get-caller-identity
# Expected: "Account": "000000000000"

# 2. Confirm pilot/web:latest exists in ECR
aws ecr describe-images \
  --repository-name pilot/web \
  --query 'imageDetails[?contains(imageTags, `latest`)].[imagePushedAt,imageSizeInBytes]' \
  --output table \
  --region us-east-1
# If empty → build and push before proceeding (see §Build & Push below)

# 3. Confirm ECS backend services are healthy
aws ecs describe-services \
  --cluster pilot-production \
  --services pilot-api pilot-celery-worker pilot-celery-beat \
  --query 'services[*].{Name:serviceName,Running:runningCount,Desired:desiredCount,Status:status}' \
  --output table \
  --region us-east-1
# Expected: all ACTIVE, all running == desired

# 4. Confirm pilot-web service does NOT exist yet
aws ecs describe-services \
  --cluster pilot-production \
  --services pilot-web \
  --query 'services[0].status' \
  --output text \
  --region us-east-1
# Expected: INACTIVE or "None" — if ACTIVE, this step was already done

# 5. Check current IP (may need bastion SG update)
curl -s https://api.ipify.org
```

---

## If `pilot/web:latest` Is Not in ECR

Build and push the image before applying Terraform:

```bash
# ECR login
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  000000000000.dkr.ecr.us-east-1.amazonaws.com

# Build from repo root (linux/amd64 required — ECS Fargate is x86_64)
cd frontend
docker build --platform linux/amd64 -t pilot-web -f apps/web/Dockerfile .

# Tag and push
docker tag pilot-web:latest \
  000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/web:latest
docker push \
  000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/web:latest
```

> **Health check**: `GET /api/health` on port 3000 must return HTTP 200. Confirm locally before pushing:
> ```bash
> docker run -p 3000:3000 pilot-web
> curl -sI http://localhost:3000/api/health
> ```

---

## Task A — Terraform: Update `modules/compute/main.tf`

Make the following changes to [`infrastructure/terraform/modules/compute/main.tf`](../../../infrastructure/terraform/modules/compute/main.tf):

### A1. Remove `aws_apprunner_service.web` resource block

Delete the entire `resource "aws_apprunner_service" "web" { ... }` block.

### A2. Add `aws_security_group.sg_web`

```hcl
resource "aws_security_group" "sg_web" {
  name        = "${var.project_name}-${var.environment}-sg-web"
  description = "pilot-web ECS service — allows ALB to reach Next.js on port 3000"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Next.js from ALB"
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.sg_alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, {
    Name      = "${var.project_name}-${var.environment}-sg-web"
    Component = "web-dashboard"
    Service   = "web-dashboard"
  })
}
```

### A3. Add `aws_lb_target_group.web`

```hcl
resource "aws_lb_target_group" "web" {
  name        = "${var.project_name}-${var.environment}-web"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"   # Required for Fargate awsvpc networking

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

  tags = merge(var.common_tags, {
    Name      = "${var.project_name}-${var.environment}-web-tg"
    Component = "web-dashboard"
    Service   = "web-dashboard"
  })
}
```

### A4. Add `aws_lb_listener_rule.web`

```hcl
resource "aws_lb_listener_rule" "web" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 10   # Lower number = higher priority; evaluated before catch-all API rule

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web.arn
  }

  condition {
    host_header {
      values = ["app.pilotfortrades.com"]
    }
  }

  tags = merge(var.common_tags, {
    Name      = "${var.project_name}-${var.environment}-web-listener-rule"
    Component = "web-dashboard"
  })
}
```

### A5. Add `aws_ecs_task_definition.web`

```hcl
resource "aws_ecs_task_definition" "web" {
  family                   = "${var.project_name}-${var.environment}-web"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"    # 0.5 vCPU
  memory                   = "1024"   # 1024 MB

  execution_role_arn = var.ecs_execution_role_arn
  task_role_arn      = var.ecs_task_role_arn

  container_definitions = jsonencode([{
    name  = "web"
    image = "${aws_ecr_repository.web.repository_url}:latest"
    portMappings = [{
      containerPort = 3000
      protocol      = "tcp"
    }]
    environment = [
      { name = "NEXT_PUBLIC_API_URL",              value = "https://api.pilotfortrades.com" },
      { name = "NEXT_PUBLIC_COGNITO_REGION",       value = "us-east-1" },
      { name = "NEXT_PUBLIC_COGNITO_USER_POOL_ID", value = var.cognito_user_pool_id },
      { name = "NEXT_PUBLIC_COGNITO_APP_CLIENT_ID",value = var.cognito_app_client_id },
      { name = "NEXT_PUBLIC_USE_MOCK_AUTH",         value = "false" },
      { name = "NEXT_PUBLIC_USE_MSW_MOCKS",         value = "false" },
      { name = "NODE_ENV",                          value = "production" }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/ecs/${var.project_name}-${var.environment}-web"
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:3000/api/health || exit 1"]
      interval    = 30
      timeout     = 10
      retries     = 3
      startPeriod = 60
    }
  }])

  tags = merge(var.common_tags, {
    Name      = "${var.project_name}-${var.environment}-web"
    Component = "web-dashboard"
    Service   = "web-dashboard"
  })
}
```

### A6. Add `aws_ecs_service.web`

```hcl
resource "aws_ecs_service" "web" {
  name            = "${var.project_name}-web"
  cluster         = aws_ecs_cluster.main.id
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

  depends_on = [aws_lb_listener_rule.web]

  tags = merge(var.common_tags, {
    Name      = "${var.project_name}-${var.environment}-web-service"
    Component = "web-dashboard"
    Service   = "web-dashboard"
  })
}
```

### A7. Add CloudWatch Log Group for `pilot-web`

```hcl
resource "aws_cloudwatch_log_group" "web" {
  name              = "/ecs/${var.project_name}-${var.environment}-web"
  retention_in_days = 30

  tags = merge(var.common_tags, {
    Name      = "/ecs/${var.project_name}-${var.environment}-web"
    Component = "web-dashboard"
    Service   = "web-dashboard"
  })
}
```

### A8. Update `aws_route53_record.app` (CNAME → A alias)

Find the existing `app.pilotfortrades.com` record and replace the CNAME type with an A alias pointing to the same ALB as the API:

```hcl
resource "aws_route53_record" "app" {
  zone_id = var.route53_zone_id
  name    = "app.pilotfortrades.com"
  type    = "A"

  alias {
    name                   = aws_lb.api.dns_name
    zone_id                = aws_lb.api.zone_id
    evaluate_target_health = true
  }
}
```

> **Important**: Delete the old CNAME record type block entirely. The TTL and `records` fields are not used with alias records.

---

## Task B — Terraform: Update `modules/compute/outputs.tf`

Remove `app_runner_service_url` and `app_runner_service_arn` outputs (they no longer exist). Add a web service output:

```hcl
output "web_service_name" {
  description = "ECS service name for the Next.js web dashboard"
  value       = aws_ecs_service.web.name
}
```

---

## Task C — Terraform: Update `modules/security/main.tf`

Remove the App Runner IAM role and its policy attachment — they are no longer needed:

```hcl
# DELETE these two blocks:
resource "aws_iam_role" "app_runner" { ... }
resource "aws_iam_role_policy_attachment" "app_runner_ecr" { ... }
```

> **Search for** `app_runner` in `modules/security/main.tf` to find the exact block names.

---

## Task D — Update `infrastructure/scripts/generate-infra-state.sh`

1. **Remove** the `APP_RUNNER_ARN` variable and its discovery logic:
   - Delete the line: `APP_RUNNER_ARN=$(tf_output "app_runner_service_arn" || echo "")`
   - Delete the line: `[ -n "$APP_RUNNER_ARN" ] && INFRA_APP_RUNNER="true" || INFRA_APP_RUNNER="false"`
   - Delete `APP_RUNNER_ARN="$APP_RUNNER_ARN"` from the written state block
   - Delete `INFRA_APP_RUNNER="$INFRA_APP_RUNNER"` from the written state block

2. **Update `INFRA_ECS`** to check for all 4 services (including `pilot-web`):

```bash
# Replace the existing INFRA_ECS detection logic with:
if aws ecs describe-services \
    --cluster "${CLUSTER_NAME:-pilot-production}" \
    --services pilot-api pilot-celery-worker pilot-celery-beat pilot-web \
    --query 'services[?status==`ACTIVE`] | length(@)' \
    --output text \
    --region "${AWS_DEFAULT_REGION:-us-east-1}" 2>/dev/null | grep -q "^4$"; then
  INFRA_ECS="true"
else
  INFRA_ECS="false"
fi
```

3. **Update the echo output** to remove `INFRA_APP_RUNNER` line and update `INFRA_ECS` description.

4. **Also update `.infra-state.env.example`** — remove `APP_RUNNER_ARN` and `INFRA_APP_RUNNER` lines.

---

## Task E — Update All 4 Profile Scripts

In each of `profile-off.sh`, `profile-a-marketing.sh`, `profile-b-app.sh`, `profile-c-checklist.sh`:

### E1. Remove App Runner blocks

Delete any block like:
```bash
if [ "$INFRA_APP_RUNNER" = "true" ] && [ -n "$APP_RUNNER_ARN" ]; then
  aws apprunner pause-service --service-arn "$APP_RUNNER_ARN" ...
  # or resume-service
fi
```

### E2. Replace with `pilot-web` ECS desired-count blocks

**Profile OFF and Profile A** (web dashboard should be at 0 tasks):
```bash
if [ "$INFRA_ECS" = "true" ]; then
  echo "[N/M] ECS pilot-web → scaling to 0..."
  aws ecs update-service \
    --cluster pilot-production \
    --service pilot-web \
    --desired-count 0 \
    --region us-east-1 > /dev/null
  echo "[N/M] ECS pilot-web → ✅ desired-count=0"
else
  echo "[N/M] ECS pilot-web → [SKIP] not yet provisioned (Phase 6 Step 6.4)"
fi
```

**Profile B light, Profile B ai, Profile C** (web dashboard should be at 1 task):
```bash
if [ "$INFRA_ECS" = "true" ]; then
  echo "[N/M] ECS pilot-web → scaling to 1..."
  aws ecs update-service \
    --cluster pilot-production \
    --service pilot-web \
    --desired-count 1 \
    --region us-east-1 > /dev/null
  echo "[N/M] ECS pilot-web → ✅ desired-count=1"
else
  echo "[N/M] ECS pilot-web → [SKIP] not yet provisioned (Phase 6 Step 6.4)"
fi
```

### E3. Update health check in `profile-c-checklist.sh`

Replace the App Runner health check with:
```bash
# Health check 3: ECS pilot-web running
WEB_RUNNING=$(aws ecs describe-services \
  --cluster pilot-production \
  --services pilot-web \
  --query 'services[0].runningCount' \
  --output text \
  --region us-east-1 2>/dev/null || echo "0")
if [ "$WEB_RUNNING" -ge "1" ]; then
  echo "✅ [3/7] ECS pilot-web: $WEB_RUNNING task(s) running"
else
  echo "❌ [3/7] ECS pilot-web: 0 tasks running"
  CHECKS_FAILED=$((CHECKS_FAILED+1))
fi

# Health check 6: Web dashboard HTTP 200
WEB_STATUS=$(curl -sI https://app.pilotfortrades.com | head -1 | awk '{print $2}')
if [ "$WEB_STATUS" = "200" ]; then
  echo "✅ [6/7] Web dashboard: HTTP $WEB_STATUS"
else
  echo "❌ [6/7] Web dashboard: HTTP $WEB_STATUS (expected 200)"
  CHECKS_FAILED=$((CHECKS_FAILED+1))
fi
```

---

## Task F — Apply Terraform

```bash
cd infrastructure/terraform/environments/production

# Plan first to review changes
terraform plan -target=module.compute -target=module.security -out=plan-step-6-4.tfplan

# Review plan carefully — should show:
# + aws_security_group.sg_web (or module.compute.aws_security_group.sg_web)
# + aws_lb_target_group.web
# + aws_lb_listener_rule.web
# + aws_ecs_task_definition.web
# + aws_ecs_service.web
# + aws_cloudwatch_log_group.web
# ~ aws_route53_record.app (CNAME → A alias)
# - aws_iam_role.app_runner (or via module.security)
# - aws_iam_role_policy_attachment.app_runner_ecr
# No unexpected destroys (verify before applying)

terraform apply plan-step-6-4.tfplan
```

---

## Task G — Verify

```bash
# 1. ECS pilot-web service ACTIVE
aws ecs describe-services \
  --cluster pilot-production \
  --services pilot-web \
  --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount}' \
  --output table \
  --region us-east-1
# Expected: ACTIVE, Running=1, Desired=1

# 2. Wait for service stability
aws ecs wait services-stable \
  --cluster pilot-production \
  --services pilot-web \
  --region us-east-1
echo "pilot-web stable ✅"

# 3. Web dashboard HTTP 200
curl -sI https://app.pilotfortrades.com | head -3
# Expected: HTTP/2 200

# 4. Health endpoint responds
curl -sf https://app.pilotfortrades.com/api/health
# Expected: HTTP 200 JSON response

# 5. Regenerate infra state
cd infrastructure/scripts
./generate-infra-state.sh
# Expected: INFRA_ECS=true (all 4 services active)
# INFRA_APP_RUNNER should NOT appear

# 6. Run profile-off.sh dry run (confirm no App Runner references remain)
./profile-off.sh
# Expected: no "apprunner" in output; pilot-web scales to 0 tasks
```

---

## Task H — Update `aws-deployment-status.md`

In [`dev-docs/devops/aws-deployment-status.md`](../aws-deployment-status.md):

1. Update Phase 6 Step 6.4 status to ✅ Complete with date
2. Fill in verification results:
   - `pilot-web` ECS service ACTIVE ✅
   - `app.pilotfortrades.com` HTTP 200 ✅
3. Update Terraform State section `Last apply` to include this apply
4. Add any issues encountered to the Issues Log

---

## Definition of Done

- [ ] `aws_apprunner_service.web` removed from Terraform state
- [ ] `aws_iam_role.app_runner` removed from Terraform state
- [ ] `aws_security_group.sg_web` created
- [ ] `aws_lb_target_group.web` created (port 3000, health check `/api/health`)
- [ ] `aws_lb_listener_rule.web` created (`Host: app.pilotfortrades.com`, priority 10)
- [ ] `aws_ecs_task_definition.web` created (0.5 vCPU / 1024MB)
- [ ] `aws_ecs_service.web` ACTIVE — `pilot-web` running 1/1 tasks
- [ ] `/ecs/pilot-production-web` CloudWatch log group created
- [ ] `app.pilotfortrades.com` DNS: A alias → ALB (not CNAME)
- [ ] `curl https://app.pilotfortrades.com/api/health` → HTTP 200
- [ ] `generate-infra-state.sh`: `INFRA_APP_RUNNER` removed; `INFRA_ECS=true` after apply
- [ ] All 4 profile scripts: App Runner pause/resume replaced with ECS desired-count 0/1
- [ ] `profile-c-checklist.sh`: App Runner health check replaced with ECS pilot-web check
- [ ] `aws-deployment-status.md` Step 6.4 marked ✅ Complete

---

## File Reference

| File | Change |
|---|---|
| [`infrastructure/terraform/modules/compute/main.tf`](../../../infrastructure/terraform/modules/compute/main.tf) | Remove apprunner; add sg-web, TG, listener rule, task def, service, CW log group; update Route53 record |
| [`infrastructure/terraform/modules/compute/outputs.tf`](../../../infrastructure/terraform/modules/compute/outputs.tf) | Remove app_runner outputs; add web_service_name |
| [`infrastructure/terraform/modules/security/main.tf`](../../../infrastructure/terraform/modules/security/main.tf) | Remove app_runner IAM role + policy attachment |
| [`infrastructure/scripts/generate-infra-state.sh`](../../../infrastructure/scripts/generate-infra-state.sh) | Remove APP_RUNNER_ARN / INFRA_APP_RUNNER; update INFRA_ECS to check 4 services |
| [`infrastructure/scripts/.infra-state.env.example`](../../../infrastructure/scripts/.infra-state.env.example) | Remove APP_RUNNER_ARN / INFRA_APP_RUNNER lines |
| [`infrastructure/scripts/profile-off.sh`](../../../infrastructure/scripts/profile-off.sh) | Replace App Runner pause with ECS pilot-web desired-count 0 |
| [`infrastructure/scripts/profile-a-marketing.sh`](../../../infrastructure/scripts/profile-a-marketing.sh) | Replace App Runner pause with ECS pilot-web desired-count 0 |
| [`infrastructure/scripts/profile-b-app.sh`](../../../infrastructure/scripts/profile-b-app.sh) | Replace App Runner resume with ECS pilot-web desired-count 1 |
| `infrastructure/scripts/profile-c-checklist.sh` _(private)_ | Replace App Runner resume + health check with ECS pilot-web desired-count 1 + HTTP check |
| [`dev-docs/devops/aws-deployment-status.md`](../aws-deployment-status.md) | Step 6.4 status ✅; Terraform state last apply update |

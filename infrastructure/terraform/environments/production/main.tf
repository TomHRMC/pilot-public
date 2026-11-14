# ─── Pilot for Trades — Production Environment ────────────────────────────────
# Deploy from this directory:
#   cd infrastructure/terraform/environments/production
#   terraform init
#   terraform plan
#   terraform apply
#
# Account: HotRMC (owner@example.com) — ID: 000000000000
# Region: us-east-1
#
# ONE-TIME BOOTSTRAP (before terraform init):
#   See aws-deployment-plan-v1.md §5 Phase 1.1 for S3 + DynamoDB setup commands
#
# COGNITO IMPORT (before first apply — pool already exists):
#   terraform import aws_cognito_user_pool.prod us-east-1_XXXXXXXXX
#   terraform import aws_cognito_user_pool_client.prod_web us-east-1_XXXXXXXXX/xxxxxxxxxxxxxxxxxxxxxxxxxx

terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

provider "aws" {
  region = var.aws_region

  # Default tags applied to EVERY resource per aws-deployment-plan-v1.md §11.4
  default_tags {
    tags = {
      Project     = "pilot-for-trades"
      Environment = var.environment
      Owner       = "owner"
      ManagedBy   = "terraform"
      CostCenter  = "infrastructure"
    }
  }
}

# ─── Module: Networking ───────────────────────────────────────────────────────

module "networking" {
  source = "../../modules/networking"

  environment          = var.environment
  vpc_cidr             = var.vpc_cidr
  admin_allowed_ips    = var.admin_allowed_ips
  tom_admin_public_key = var.tom_admin_public_key
}

# ─── Module: Security ─────────────────────────────────────────────────────────

module "security" {
  source = "../../modules/security"

  environment           = var.environment
  aws_region            = var.aws_region
  account_id            = var.account_id
  domain_name           = var.domain_name
  github_repo           = var.github_repo
  cognito_user_pool_id  = var.cognito_user_pool_id
  cognito_app_client_id = var.cognito_app_client_id
  # MFA-WIRE-1 (Step 0): ExternalId for the Cognito→SNS assume-role trust.
  # Configuration value (not a secret) — explicit here rather than relying on
  # the module default, so auth-critical infra is visible at the env level.
  cognito_sms_external_id = "pilot-prod-cognito-sms"

  vpc_id             = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids
  sg_lambda_id       = module.networking.sg_lambda_id

  depends_on = [module.networking]
}

# ─── Module: Storage ──────────────────────────────────────────────────────────

module "storage" {
  source = "../../modules/storage"

  environment = var.environment
  kms_key_arn = module.security.kms_key_arn
  account_id  = var.account_id
  # cloudfront_oac_arn updated after compute module runs:
  # terraform apply -target=module.compute then re-apply to update bucket policy
  cloudfront_oac_arn = try(module.compute.cloudfront_oac_arn, "")

  depends_on = [module.security]
}

# ─── Module: Database ─────────────────────────────────────────────────────────

module "database" {
  source = "../../modules/database"

  environment       = var.environment
  db_instance_class = var.db_instance_class
  db_name           = var.db_name
  db_username       = var.db_username
  kms_key_arn       = module.security.kms_key_arn

  private_subnet_ids = module.networking.private_subnet_ids
  sg_rds_id          = module.networking.sg_rds_id
  sg_redis_id        = module.networking.sg_redis_id

  # Secret shells created by security module
  secret_db_arn    = module.security.secret_db_arn
  secret_redis_arn = module.security.secret_redis_arn

  depends_on = [module.networking, module.security]
}

# ─── Module: Compute ──────────────────────────────────────────────────────────

module "compute" {
  source = "../../modules/compute"

  environment              = var.environment
  aws_region               = var.aws_region
  account_id               = var.account_id
  domain_name              = var.domain_name
  gpu_ami_id               = var.gpu_ami_id
  ecs_api_desired_count    = var.ecs_api_desired_count
  ecs_worker_desired_count = var.ecs_worker_desired_count

  vpc_id             = module.networking.vpc_id
  public_subnet_ids  = module.networking.public_subnet_ids
  private_subnet_ids = module.networking.private_subnet_ids
  sg_alb_id          = module.networking.sg_alb_id
  sg_ecs_api_id      = module.networking.sg_ecs_api_id
  sg_gpu_id          = module.networking.sg_gpu_id
  bastion_key_name   = module.networking.bastion_key_name

  kms_key_arn            = module.security.kms_key_arn
  ecs_task_role_arn      = module.security.ecs_task_role_arn
  ecs_execution_role_arn = module.security.ecs_execution_role_arn
  acm_certificate_arn    = module.security.acm_certificate_arn
  # C-B16-OPS (ADR-0014): p4tsites.com cert ARN for SNI on shared ALB
  p4tsites_certificate_arn = module.security.p4tsites_certificate_arn
  cognito_user_pool_id     = var.cognito_user_pool_id
  cognito_app_client_id    = var.cognito_app_client_id

  secret_db_arn          = module.security.secret_db_arn
  secret_sendgrid_arn    = module.security.secret_sendgrid_arn
  secret_telnyx_arn      = module.security.secret_telnyx_arn
  secret_stripe_arn      = module.security.secret_stripe_arn
  secret_quickbooks_arn  = module.security.secret_quickbooks_arn
  secret_encryption_arn  = module.security.secret_encryption_arn
  secret_cognito_arn     = module.security.secret_cognito_arn
  secret_google_maps_arn = module.security.secret_google_maps_arn
  secret_turnstile_arn   = module.security.secret_turnstile_arn
  secret_redis_arn       = module.security.secret_redis_arn
  route53_zone_id        = module.security.route53_zone_id
  gpu_quota_approved     = var.gpu_quota_approved
  acm_cert_validated     = var.acm_cert_validated
  ecr_images_available   = var.ecr_images_available

  depends_on = [module.networking, module.security, module.database]
}

# ─── Module: Monitoring ───────────────────────────────────────────────────────

module "monitoring" {
  source = "../../modules/monitoring"

  environment                   = var.environment
  aws_region                    = var.aws_region
  alarm_email                   = var.alarm_email
  cloudwatch_log_retention_days = var.cloudwatch_log_retention_days

  alb_arn_suffix         = module.compute.alb_arn_suffix
  ecs_cluster_name       = module.compute.ecs_cluster_name
  rds_identifier         = module.database.rds_identifier
  elasticache_cluster_id = module.database.elasticache_cluster_id
  gpu_instance_id        = module.compute.gpu_instance_id
  gpu_quota_approved     = var.gpu_quota_approved

  depends_on = [module.compute, module.database]
}

# ─── Outputs (pass-through from root outputs.tf) ──────────────────────────────

output "bastion_public_ip" {
  description = "Bastion host public IP — add to ~/.ssh/config as HostName for pilot-bastion"
  value       = module.networking.bastion_public_ip
}

output "nat_gateway_eip" {
  description = "NAT Gateway EIP — add to Google Maps API key IP allowlist after Phase 1"
  value       = module.networking.nat_gateway_eip
}

output "route53_nameservers" {
  description = "⚠️  Copy these 4 NS records into GoDaddy before switching (Phase 5 DNS migration §7.2 Step F)"
  value       = module.security.route53_nameservers
}

output "ecr_api_url" {
  description = "ECR URL for pilot/api — used in bootstrap docker push"
  value       = module.compute.ecr_api_url
}

output "ecr_worker_url" {
  value = module.compute.ecr_worker_url
}

output "ecr_beat_url" {
  value = module.compute.ecr_beat_url
}

output "ecr_web_url" {
  value = module.compute.ecr_web_url
}

output "cloudfront_distribution_id" {
  description = "Set as GitHub Actions secret CLOUDFRONT_DISTRIBUTION_ID"
  value       = module.compute.cloudfront_distribution_id
}

output "gpu_private_ip" {
  description = "After GPU is running, populate pilot/prod/gpu in Secrets Manager:\n  {\"whisper_url\": \"http://<IP>:8080/v1\", \"ollama_url\": \"http://<IP>:11434/api\"}"
  value       = module.compute.gpu_private_ip
}

output "rds_endpoint" {
  description = "RDS endpoint — for SSH tunnel: ssh -L 5432:<this>:5432 pilot-bastion -N"
  value       = module.database.rds_endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "Redis endpoint — for SSH tunnel: ssh -L 6379:<this>:6379 pilot-bastion -N"
  value       = module.database.redis_endpoint
  sensitive   = true
}

output "github_actions_role_arn" {
  description = "Embed in .github/workflows/deploy-production.yml role-to-assume"
  value       = module.security.github_actions_role_arn
}

output "sns_alarm_topic_arn" {
  description = "SNS alarm topic — check email for subscription confirmation after first apply"
  value       = module.monitoring.sns_alarm_topic_arn
}

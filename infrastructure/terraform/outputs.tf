# ─── Networking Outputs ───────────────────────────────────────────────────────

output "vpc_id" {
  description = "VPC ID"
  value       = module.networking.vpc_id
}

output "public_subnet_ids" {
  description = "Public subnet IDs (us-east-1a, us-east-1b)"
  value       = module.networking.public_subnet_ids
}

output "private_subnet_ids" {
  description = "Private subnet IDs (us-east-1a, us-east-1b)"
  value       = module.networking.private_subnet_ids
}

output "bastion_public_ip" {
  description = "Bastion host public IP — update ~/.ssh/config HostName for pilot-bastion"
  value       = module.networking.bastion_public_ip
}

output "nat_gateway_eip" {
  description = "NAT Gateway Elastic IP — add to Google Maps API key IP restrictions"
  value       = module.networking.nat_gateway_eip
}

# ─── Compute Outputs ──────────────────────────────────────────────────────────

output "alb_dns_name" {
  description = "ALB DNS name — used in Route 53 alias record for api.pilotfortrades.com"
  value       = module.compute.alb_dns_name
}

output "alb_zone_id" {
  description = "ALB hosted zone ID — used in Route 53 alias record"
  value       = module.compute.alb_zone_id
}

output "ecr_api_url" {
  description = "ECR repository URL for pilot/api image"
  value       = module.compute.ecr_api_url
}

output "ecr_worker_url" {
  description = "ECR repository URL for pilot/worker image"
  value       = module.compute.ecr_worker_url
}

output "ecr_beat_url" {
  description = "ECR repository URL for pilot/beat image"
  value       = module.compute.ecr_beat_url
}

output "ecr_web_url" {
  description = "ECR repository URL for pilot/web image"
  value       = module.compute.ecr_web_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name for CI/CD deploy commands"
  value       = module.compute.ecs_cluster_name
}

output "gpu_private_ip" {
  description = "GPU instance private IP — used in ECS environment vars for WHISPER_API_URL and OLLAMA_API_URL"
  value       = module.compute.gpu_private_ip
}

output "app_runner_service_url" {
  description = "Legacy output from the pre-ADR-0001 App Runner design (App Runner was sunset Apr 2026; the web app now runs as the pilot-web ECS service behind the ALB). The referenced module output no longer exists — the active configuration is environments/production."
  value       = module.compute.app_runner_service_url
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID — used in CI/CD for cache invalidation (set as GitHub secret CLOUDFRONT_DISTRIBUTION_ID)"
  value       = module.compute.cloudfront_distribution_id
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name — used in Route 53 alias for pilotfortrades.com"
  value       = module.compute.cloudfront_domain_name
}

# ─── Database Outputs ─────────────────────────────────────────────────────────

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint — used in SSH tunnel command: ssh -L 5432:<this>:5432 pilot-bastion"
  value       = module.database.rds_endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint — used in SSH tunnel command: ssh -L 6379:<this>:6379 pilot-bastion"
  value       = module.database.redis_endpoint
  sensitive   = true
}

# ─── Security Outputs ─────────────────────────────────────────────────────────

output "cognito_user_pool_id" {
  description = "Production Cognito user pool ID"
  value       = module.security.cognito_user_pool_id
}

output "cognito_app_client_id" {
  description = "Production Cognito app client ID"
  value       = module.security.cognito_app_client_id
}

output "kms_key_arn" {
  description = "Customer-managed KMS key ARN"
  value       = module.security.kms_key_arn
}

output "github_actions_role_arn" {
  description = "GitHub Actions OIDC IAM role ARN — embed in .github/workflows/deploy-production.yml"
  value       = module.security.github_actions_role_arn
}

output "route53_zone_id" {
  description = "Route 53 hosted zone ID for pilotfortrades.com"
  value       = module.security.route53_zone_id
}

output "route53_nameservers" {
  description = "Route 53 nameservers — enter these in GoDaddy nameserver settings during DNS migration (Phase 5 §7.2)"
  value       = module.security.route53_nameservers
}

output "acm_certificate_arn" {
  description = "ACM wildcard certificate ARN"
  value       = module.security.acm_certificate_arn
}

# ─── Monitoring Outputs ───────────────────────────────────────────────────────

output "sns_alarm_topic_arn" {
  description = "SNS topic ARN for CloudWatch alarm notifications"
  value       = module.monitoring.sns_alarm_topic_arn
}

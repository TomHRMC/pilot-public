variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "account_id" {
  description = "AWS account ID"
  type        = string
}

variable "domain_name" {
  description = "Root domain name"
  type        = string
}

variable "gpu_ami_id" {
  description = "AMI ID for the EC2 GPU instance (AWS Deep Learning AMI Amazon Linux 2 with NVIDIA drivers)"
  type        = string
}

variable "ecs_api_desired_count" {
  description = "Desired number of ECS tasks for the FastAPI API service"
  type        = number
  default     = 2
}

variable "ecs_worker_desired_count" {
  description = "Desired number of ECS tasks for the Celery Worker service"
  type        = number
  default     = 2
}

# ─── Networking inputs ────────────────────────────────────────────────────────

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for ALB"
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for ECS, GPU, RDS"
  type        = list(string)
}

variable "sg_alb_id" {
  description = "ALB security group ID"
  type        = string
}

variable "sg_ecs_api_id" {
  description = "ECS API tasks security group ID"
  type        = string
}

variable "sg_gpu_id" {
  description = "GPU instance security group ID"
  type        = string
}

variable "bastion_key_name" {
  description = "EC2 key pair name for GPU instance SSH access"
  type        = string
}

# ─── Security inputs ──────────────────────────────────────────────────────────

variable "kms_key_arn" {
  description = "KMS key ARN for EBS encryption"
  type        = string
}

variable "ecs_task_role_arn" {
  description = "ECS task IAM role ARN"
  type        = string
}

variable "ecs_execution_role_arn" {
  description = "ECS task execution IAM role ARN"
  type        = string
}

variable "acm_certificate_arn" {
  description = "ACM wildcard certificate ARN for ALB HTTPS listener"
  type        = string
}

variable "p4tsites_certificate_arn" {
  description = "ACM cert ARN for *.p4tsites.com — SNI listener certificate on shared ALB (C-B16-OPS, ADR-0014)"
  type        = string
}

variable "cognito_user_pool_id" {
  description = "Production Cognito user pool ID"
  type        = string
}

variable "cognito_app_client_id" {
  description = "Production Cognito app client ID"
  type        = string
}

# ─── Secrets Manager ARNs for ECS task injection ─────────────────────────────

variable "secret_db_arn" {
  type = string
}

variable "secret_sendgrid_arn" {
  type = string
}

variable "secret_telnyx_arn" {
  type = string
}

variable "secret_stripe_arn" {
  type = string
}

variable "secret_quickbooks_arn" {
  type = string
}

variable "secret_encryption_arn" {
  type = string
}

variable "secret_cognito_arn" {
  type = string
}

variable "secret_google_maps_arn" {
  type = string
}

variable "secret_turnstile_arn" {
  description = "Secrets Manager ARN for Cloudflare Turnstile server-side secret key"
  type        = string
}

variable "secret_redis_arn" {
  type = string
}

variable "route53_zone_id" {
  description = "Route 53 hosted zone ID for pilotfortrades.com — passed from module.security"
  type        = string
}

variable "acm_cert_validated" {
  description = "Set true after Phase 5 GoDaddy NS cutover + ACM cert validates. Gates HTTPS ALB listener and CloudFront custom domain/cert."
  type        = bool
  default     = false
}

variable "ecr_images_available" {
  description = "Set true after Phase 6 first docker push (pilot/web:latest exists). Gates creation of the api, worker, and beat ECS services."
  type        = bool
  default     = false
}

variable "gpu_quota_approved" {
  description = "Set true after AWS Service Quota increase approved for G instance vCPUs (EC2 → Running On-Demand G and VT instances). Request at: AWS Console → Service Quotas → EC2."
  type        = bool
  default     = false
}

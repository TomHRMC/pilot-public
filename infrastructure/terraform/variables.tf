# ─── Core ─────────────────────────────────────────────────────────────────────

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (production)"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["production", "staging", "development"], var.environment)
    error_message = "environment must be production, staging, or development."
  }
}

variable "domain_name" {
  description = "Root domain name for the application"
  type        = string
  default     = "pilotfortrades.com"
}

variable "account_id" {
  description = "AWS account ID for the HotRMC deployment account"
  type        = string
  default     = "000000000000"
}

# ─── Networking ───────────────────────────────────────────────────────────────

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "admin_allowed_ips" {
  description = "List of Tom's known public IPs for bastion SSH access — update when IP changes"
  type        = list(string)
  # Set in terraform.tfvars; add all known IPs (home ISP, backup ISP, VPN, hotel)
  # Current known IPs:
  #   home ISP: 203.0.113.13
  #   backup ISP: add when confirmed — run: curl -s https://api.ipify.org while on backup ISP
}

variable "tom_admin_public_key" {
  description = "Tom's SSH public key for the bastion host EC2 key pair"
  type        = string
  # Confirmed value (generated 2026-06-30):
  default = "ssh-ed25519 AAAA...REPLACE_WITH_YOUR_PUBLIC_KEY pilot-admin"
}

# ─── Compute ──────────────────────────────────────────────────────────────────

variable "gpu_ami_id" {
  description = "AMI ID for the EC2 GPU instance — AWS Deep Learning AMI (Amazon Linux 2) with NVIDIA drivers. Find in us-east-1 AMI catalog: 'Deep Learning AMI (Amazon Linux 2)'"
  type        = string
  # Set in terraform.tfvars after looking up current AMI ID in AWS Console
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

# ─── Database ─────────────────────────────────────────────────────────────────

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.micro"
}

variable "db_name" {
  description = "Name of the PostgreSQL database"
  type        = string
  default     = "pilot_prod"
}

variable "db_username" {
  description = "Master username for the RDS PostgreSQL instance"
  type        = string
  default     = "pilot_user"
}

# ─── Security ─────────────────────────────────────────────────────────────────

variable "github_repo" {
  description = "GitHub repository for OIDC trust (org/repo format)"
  type        = string
  default     = "TomHRMC/pilot"
}

variable "cognito_user_pool_id" {
  description = "Existing production Cognito user pool ID (import — do not recreate)"
  type        = string
  default     = "us-east-1_XXXXXXXXX"
}

variable "cognito_app_client_id" {
  description = "Existing production Cognito app client ID (import — do not recreate)"
  type        = string
  default     = "xxxxxxxxxxxxxxxxxxxxxxxxxx"
}

variable "cloudflare_turnstile_site_key" {
  description = "Cloudflare Turnstile public site key for marketing forms (not sensitive — public key)"
  type        = string
  default     = "0x4AAAAAADtbEEHD6Y-jXDbC"
}

# ─── Monitoring ───────────────────────────────────────────────────────────────

variable "alarm_email" {
  description = "Email address for CloudWatch alarm SNS notifications"
  type        = string
  default     = "support@pilotfortrades.com"
}

variable "cloudwatch_log_retention_days" {
  description = "CloudWatch log group retention period in days"
  type        = number
  default     = 30
}

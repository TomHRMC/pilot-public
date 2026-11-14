# Variables for the production environment
# Values are set in terraform.tfvars (not committed to git)

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "environment" {
  type    = string
  default = "production"
}

variable "account_id" {
  type    = string
  default = "000000000000"
}

variable "domain_name" {
  type    = string
  default = "pilotfortrades.com"
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "admin_allowed_ips" {
  type = list(string)
}

variable "tom_admin_public_key" {
  type    = string
  default = "ssh-ed25519 AAAA...REPLACE_WITH_YOUR_PUBLIC_KEY pilot-admin"
}

variable "gpu_ami_id" {
  type        = string
  description = "Deep Learning AMI ID for us-east-1 — find current AMI in AWS Console"
}

variable "ecs_api_desired_count" {
  type    = number
  default = 2
}

variable "ecs_worker_desired_count" {
  type    = number
  default = 2
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "db_name" {
  type    = string
  default = "pilot_prod"
}

variable "db_username" {
  type    = string
  default = "pilot_user"
}

variable "github_repo" {
  type    = string
  default = "TomHRMC/pilot"
}

variable "cognito_user_pool_id" {
  type    = string
  default = "us-east-1_XXXXXXXXX"
}

variable "cognito_app_client_id" {
  type    = string
  default = "xxxxxxxxxxxxxxxxxxxxxxxxxx"
}

variable "cloudflare_turnstile_site_key" {
  type    = string
  default = "0x4AAAAAADtbEEHD6Y-jXDbC"
}

variable "alarm_email" {
  type    = string
  default = "tom@pilotfortrades.com"
}

variable "cloudwatch_log_retention_days" {
  type    = number
  default = 30
}

variable "gpu_quota_approved" {
  type        = bool
  description = "Set true after AWS Service Quota increase approved for G instance vCPUs. Request at: Service Quotas → EC2 → Running On-Demand G and VT instances."
  default     = false
}

variable "acm_cert_validated" {
  type        = bool
  description = "Set true after Phase 5 GoDaddy NS cutover + ACM cert issues. Enables ALB HTTPS listener and CloudFront custom domain aliases."
  default     = false
}

variable "ecr_images_available" {
  type        = bool
  description = "Set true after Phase 6 first docker push. Enables the gated ECS services (api, worker, beat)."
  default     = false
}

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

variable "github_repo" {
  description = "GitHub repository for OIDC trust (org/repo)"
  type        = string
}

variable "cognito_user_pool_id" {
  description = "Existing production Cognito user pool ID (import, not create)"
  type        = string
}

variable "cognito_app_client_id" {
  description = "Existing production Cognito app client ID (import, not create)"
  type        = string
}

variable "cognito_sms_external_id" {
  description = "ExternalId for the Cognito→SNS assume-role trust (MFA-WIRE-1). Configuration value, not a secret — lives in Terraform, not Secrets Manager."
  type        = string
  default     = "pilot-prod-cognito-sms"
}

variable "vpc_id" {
  description = "VPC ID for Lambda VPC config"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for Lambda VPC config"
  type        = list(string)
}

variable "sg_lambda_id" {
  description = "Lambda security group ID"
  type        = string
}

variable "assets_bucket_arn" {
  description = "S3 assets bucket ARN for ECS task IAM policy"
  type        = string
  default     = ""
}

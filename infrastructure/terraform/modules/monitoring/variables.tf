variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "alarm_email" {
  description = "Email address for CloudWatch alarm SNS notifications"
  type        = string
}

variable "cloudwatch_log_retention_days" {
  description = "CloudWatch log group retention period in days"
  type        = number
  default     = 30
}

variable "alb_arn_suffix" {
  description = "ALB ARN suffix for CloudWatch metrics"
  type        = string
}

variable "ecs_cluster_name" {
  description = "ECS cluster name for CloudWatch metrics"
  type        = string
}

variable "rds_identifier" {
  description = "RDS instance identifier for CloudWatch alarms"
  type        = string
}

variable "elasticache_cluster_id" {
  description = "ElastiCache cluster ID for CloudWatch alarms"
  type        = string
}

variable "gpu_instance_id" {
  description = "GPU EC2 instance ID for CloudWatch status check alarm (null until gpu_quota_approved=true)"
  type        = string
  default     = null
}

variable "gpu_quota_approved" {
  description = "Set true after AWS vCPU quota increase approved for G instance types. Gates GPU CloudWatch alarm."
  type        = bool
  default     = false
}

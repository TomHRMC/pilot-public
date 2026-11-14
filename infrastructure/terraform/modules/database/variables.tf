variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.micro"
}

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "pilot_prod"
}

variable "db_username" {
  description = "PostgreSQL master username"
  type        = string
  default     = "pilot_user"
}

variable "kms_key_arn" {
  description = "KMS key ARN for RDS encryption at rest"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for RDS subnet group"
  type        = list(string)
}

variable "sg_rds_id" {
  description = "Security group ID for RDS"
  type        = string
}

variable "sg_redis_id" {
  description = "Security group ID for ElastiCache Redis"
  type        = string
}

variable "secret_db_arn" {
  description = "Secrets Manager secret ARN for DB credentials (shell created by security module)"
  type        = string
}

variable "secret_redis_arn" {
  description = "Secrets Manager secret ARN for Redis connection info (shell created by security module)"
  type        = string
}

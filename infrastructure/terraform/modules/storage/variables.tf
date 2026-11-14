variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "kms_key_arn" {
  description = "KMS key ARN for S3 server-side encryption"
  type        = string
}

variable "account_id" {
  description = "AWS account ID for bucket policies"
  type        = string
}

variable "cloudfront_oac_arn" {
  description = "CloudFront Origin Access Control ARN for the marketing bucket policy"
  type        = string
  default     = ""
}

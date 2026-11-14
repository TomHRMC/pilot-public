output "assets_bucket_name" {
  description = "S3 assets bucket name"
  value       = aws_s3_bucket.assets.id
}

output "assets_bucket_arn" {
  description = "S3 assets bucket ARN — used in ECS task IAM policy"
  value       = aws_s3_bucket.assets.arn
}

output "marketing_bucket_name" {
  description = "S3 marketing site bucket name"
  value       = aws_s3_bucket.marketing.id
}

output "marketing_bucket_arn" {
  description = "S3 marketing site bucket ARN"
  value       = aws_s3_bucket.marketing.arn
}

output "marketing_bucket_regional_domain" {
  description = "S3 marketing bucket regional domain — used as CloudFront origin"
  value       = aws_s3_bucket.marketing.bucket_regional_domain_name
}

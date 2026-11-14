output "alb_dns_name" {
  description = "ALB DNS name — used in Route 53 A alias record for api.pilotfortrades.com"
  value       = aws_lb.api.dns_name
}

output "alb_zone_id" {
  description = "ALB hosted zone ID — used in Route 53 alias record"
  value       = aws_lb.api.zone_id
}

output "alb_arn_suffix" {
  description = "ALB ARN suffix — used in CloudWatch alarm metrics"
  value       = aws_lb.api.arn_suffix
}

output "api_blue_target_group_arn" {
  description = "ALB blue target group ARN"
  value       = aws_lb_target_group.api_blue.arn
}

output "api_green_target_group_arn" {
  description = "ALB green target group ARN — receives 0% traffic until blue/green cutover"
  value       = aws_lb_target_group.api_green.arn
}

output "ecs_cluster_name" {
  description = "ECS cluster name — used in CI/CD deploy commands and CloudWatch alarms"
  value       = aws_ecs_cluster.production.name
}

output "ecs_cluster_arn" {
  description = "ECS cluster ARN"
  value       = aws_ecs_cluster.production.arn
}

output "ecr_api_url" {
  description = "ECR repository URL for pilot/api — used in docker push commands"
  value       = aws_ecr_repository.repos["pilot/api"].repository_url
}

output "ecr_worker_url" {
  description = "ECR repository URL for pilot/worker"
  value       = aws_ecr_repository.repos["pilot/worker"].repository_url
}

output "ecr_beat_url" {
  description = "ECR repository URL for pilot/beat"
  value       = aws_ecr_repository.repos["pilot/beat"].repository_url
}

output "ecr_web_url" {
  description = "ECR repository URL for pilot/web (Next.js web dashboard)"
  value       = aws_ecr_repository.repos["pilot/web"].repository_url
}

output "gpu_private_ip" {
  description = "GPU instance private IP — set in Secrets Manager pilot/prod/gpu as whisper_url and ollama_url after deploy (null until gpu_quota_approved=true)"
  value       = length(aws_instance.gpu) > 0 ? aws_instance.gpu[0].private_ip : null
}

output "gpu_instance_id" {
  description = "GPU EC2 instance ID — used in CloudWatch status check alarm (null until gpu_quota_approved=true)"
  value       = length(aws_instance.gpu) > 0 ? aws_instance.gpu[0].id : null
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID — set as GitHub Actions secret CLOUDFRONT_DISTRIBUTION_ID"
  value       = aws_cloudfront_distribution.marketing.id
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name (e.g. d1234abcd.cloudfront.net)"
  value       = aws_cloudfront_distribution.marketing.domain_name
}

output "cloudfront_oac_arn" {
  description = "CloudFront OAC ARN — used in S3 marketing bucket policy"
  value       = "arn:aws:cloudfront::${var.account_id}:distribution/${aws_cloudfront_distribution.marketing.id}"
}

output "web_service_name" {
  description = "ECS service name for the Next.js web dashboard (pilot-web)"
  value       = aws_ecs_service.web.name
}

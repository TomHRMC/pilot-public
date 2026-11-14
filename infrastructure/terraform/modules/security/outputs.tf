output "kms_key_arn" {
  description = "Customer-managed KMS key ARN"
  value       = aws_kms_key.pilot.arn
}

output "kms_key_id" {
  description = "Customer-managed KMS key ID"
  value       = aws_kms_key.pilot.key_id
}

output "ecs_task_role_arn" {
  description = "ECS task IAM role ARN"
  value       = aws_iam_role.ecs_task.arn
}

output "ecs_execution_role_arn" {
  description = "ECS task execution IAM role ARN"
  value       = aws_iam_role.ecs_execution.arn
}

output "lambda_execution_role_arn" {
  description = "Lambda execution IAM role ARN"
  value       = aws_iam_role.lambda_execution.arn
}

output "github_actions_role_arn" {
  description = "GitHub Actions OIDC IAM role ARN — embed in deploy-production.yml"
  value       = aws_iam_role.github_actions.arn
}

output "acm_certificate_arn" {
  description = "ACM wildcard certificate ARN — PENDING_VALIDATION until Phase 5 GoDaddy NS cutover"
  value       = aws_acm_certificate.wildcard.arn
}

output "p4tsites_certificate_arn" {
  description = "ACM cert ARN for *.p4tsites.com (SNI on shared ALB) — C-B16-OPS, ADR-0014"
  value       = aws_acm_certificate.p4tsites.arn
}

output "cognito_user_pool_id" {
  description = "Production Cognito user pool ID"
  value       = aws_cognito_user_pool.prod.id
}

output "cognito_app_client_id" {
  description = "Production Cognito app client ID"
  value       = aws_cognito_user_pool_client.prod_web.id
}

output "route53_zone_id" {
  description = "Route 53 hosted zone ID for pilotfortrades.com"
  value       = aws_route53_zone.main.zone_id
}

output "route53_nameservers" {
  description = "Route 53 nameservers — enter these in GoDaddy after DNS records are validated (Phase 5 §7.2 Step F)"
  value       = aws_route53_zone.main.name_servers
}

# Secrets Manager ARNs — passed to compute and database modules
output "secret_db_arn" {
  description = "Secrets Manager ARN for DB credentials"
  value       = aws_secretsmanager_secret.db.arn
}

output "secret_redis_arn" {
  description = "Secrets Manager ARN for Redis connection info"
  value       = aws_secretsmanager_secret.redis.arn
}

output "secret_gpu_arn" {
  description = "Secrets Manager ARN for GPU instance URLs"
  value       = aws_secretsmanager_secret.gpu.arn
}

output "secret_sendgrid_arn" {
  description = "Secrets Manager ARN for SendGrid API key"
  value       = aws_secretsmanager_secret.sendgrid.arn
}

output "secret_telnyx_arn" {
  description = "Secrets Manager ARN for Telnyx API key"
  value       = aws_secretsmanager_secret.telnyx.arn
}

output "secret_stripe_arn" {
  description = "Secrets Manager ARN for Stripe keys"
  value       = aws_secretsmanager_secret.stripe.arn
}

output "secret_quickbooks_arn" {
  description = "Secrets Manager ARN for QuickBooks credentials"
  value       = aws_secretsmanager_secret.quickbooks.arn
}

output "secret_encryption_arn" {
  description = "Secrets Manager ARN for Fernet encryption key"
  value       = aws_secretsmanager_secret.encryption.arn
}

output "secret_cognito_arn" {
  description = "Secrets Manager ARN for Cognito config"
  value       = aws_secretsmanager_secret.cognito.arn
}

output "secret_google_maps_arn" {
  description = "Secrets Manager ARN for Google Maps API key"
  value       = aws_secretsmanager_secret.google_maps.arn
}

output "secret_turnstile_arn" {
  description = "Secrets Manager ARN for Cloudflare Turnstile secret key"
  value       = aws_secretsmanager_secret.turnstile.arn
}

output "cognito_sns_role_arn" {
  description = "Cognito→SNS IAM role ARN for SMS MFA delivery (MFA-WIRE-1)"
  value       = aws_iam_role.cognito_sns.arn
}

output "post_confirmation_lambda_arn" {
  description = "Post-confirmation Lambda function ARN"
  value       = aws_lambda_function.post_confirmation.arn
}

output "post_authentication_lambda_arn" {
  description = "Post-authentication Lambda function ARN (PLATFORM-SMS-B2 new-device alert)"
  value       = aws_lambda_function.post_authentication.arn
}

output "custom_email_sender_lambda_arn" {
  description = "Custom Email Sender Lambda function ARN (COGNITO-EMAIL-1 — SendGrid auth emails)"
  value       = aws_lambda_function.custom_email_sender.arn
}

output "custom_email_sender_lambda_name" {
  description = "Custom Email Sender Lambda function name (COGNITO-EMAIL-1)"
  value       = aws_lambda_function.custom_email_sender.function_name
}

output "sns_alarm_topic_arn" {
  description = "SNS topic ARN for CloudWatch alarm notifications"
  value       = aws_sns_topic.alarms.arn
}

output "guardduty_detector_id" {
  description = "GuardDuty detector ID"
  value       = aws_guardduty_detector.pilot.id
}

output "config_s3_bucket" {
  description = "S3 bucket name for AWS Config delivery"
  value       = aws_s3_bucket.config.id
}

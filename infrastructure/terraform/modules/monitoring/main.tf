# ─── SNS Topic for Alarm Notifications ───────────────────────────────────────

resource "aws_sns_topic" "alarms" {
  name = "pilot-${var.environment}-alarms"

  tags = {
    Name           = "pilot-${var.environment}-alarms"
    Component      = "monitoring"
    CostAllocation = "security-monitoring"
  }
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

# ─── CloudWatch Log Groups ────────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "ecs_api" {
  name              = "/ecs/pilot-api"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = {
    Component      = "monitoring"
    CostAllocation = "security-monitoring"
  }
}

resource "aws_cloudwatch_log_group" "ecs_worker" {
  name              = "/ecs/pilot-celery-worker"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = {
    Component      = "monitoring"
    CostAllocation = "security-monitoring"
  }
}

resource "aws_cloudwatch_log_group" "ecs_beat" {
  name              = "/ecs/pilot-celery-beat"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = {
    Component      = "monitoring"
    CostAllocation = "security-monitoring"
  }
}

resource "aws_cloudwatch_log_group" "lambda_post_confirmation" {
  name              = "/aws/lambda/pilot-${var.environment}-post-confirmation"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = {
    Component      = "monitoring"
    CostAllocation = "security-monitoring"
  }
}

# PLATFORM-SMS-B2 (ADR-0013 / Pathway C): Post-Authentication Lambda log group.
resource "aws_cloudwatch_log_group" "lambda_post_authentication" {
  name              = "/aws/lambda/pilot-${var.environment}-post-authentication"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = {
    Component      = "monitoring"
    CostAllocation = "security-monitoring"
  }
}

# COGNITO-EMAIL-1: Custom Email Sender Lambda log group.
resource "aws_cloudwatch_log_group" "lambda_custom_email_sender" {
  name              = "/aws/lambda/pilot-${var.environment}-custom-email-sender"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = {
    Component      = "monitoring"
    CostAllocation = "security-monitoring"
  }
}

resource "aws_cloudwatch_log_group" "gpu_instance" {
  name              = "/pilot/gpu-instance"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = {
    Component      = "monitoring"
    CostAllocation = "security-monitoring"
  }
}

# ─── CloudWatch Dashboard ─────────────────────────────────────────────────────

resource "aws_cloudwatch_dashboard" "pilot" {
  dashboard_name = "pilot-${var.environment}-overview"

  dashboard_body = jsonencode({
    widgets = [
      {
        type       = "text"
        x          = 0
        y          = 0
        width      = 24
        height     = 1
        properties = { markdown = "## Pilot for Trades — Production Dashboard" }
      },
      {
        type   = "metric"
        x      = 0
        y      = 1
        width  = 12
        height = 6
        properties = {
          title  = "ALB — Request Count & 5xx Errors"
          region = var.aws_region
          period = 300
          stat   = "Sum"
          metrics = [
            ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", var.alb_arn_suffix],
            ["AWS/ApplicationELB", "HTTPCode_Target_5XX_Count", "LoadBalancer", var.alb_arn_suffix],
          ]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 1
        width  = 12
        height = 6
        properties = {
          title  = "ALB — p95 Latency"
          region = var.aws_region
          period = 300
          stat   = "p95"
          metrics = [
            ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", var.alb_arn_suffix]
          ]
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 7
        width  = 12
        height = 6
        properties = {
          title  = "ECS — CPU Utilization"
          region = var.aws_region
          period = 300
          stat   = "Average"
          metrics = [
            ["AWS/ECS", "CPUUtilization", "ClusterName", var.ecs_cluster_name, "ServiceName", "pilot-api"],
            ["AWS/ECS", "CPUUtilization", "ClusterName", var.ecs_cluster_name, "ServiceName", "pilot-celery-worker"],
          ]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 7
        width  = 12
        height = 6
        properties = {
          title  = "ECS — Memory Utilization"
          region = var.aws_region
          period = 300
          stat   = "Average"
          metrics = [
            ["AWS/ECS", "MemoryUtilization", "ClusterName", var.ecs_cluster_name, "ServiceName", "pilot-api"],
            ["AWS/ECS", "MemoryUtilization", "ClusterName", var.ecs_cluster_name, "ServiceName", "pilot-celery-worker"],
          ]
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 13
        width  = 12
        height = 6
        properties = {
          title  = "RDS — Connections & CPU"
          region = var.aws_region
          period = 300
          stat   = "Average"
          metrics = [
            ["AWS/RDS", "DatabaseConnections", "DBInstanceIdentifier", var.rds_identifier],
            ["AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", var.rds_identifier],
          ]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 13
        width  = 12
        height = 6
        properties = {
          title  = "RDS — Free Storage"
          region = var.aws_region
          period = 300
          stat   = "Average"
          metrics = [
            ["AWS/RDS", "FreeStorageSpace", "DBInstanceIdentifier", var.rds_identifier]
          ]
        }
      }
    ]
  })
}

# ─── CloudWatch Alarms ────────────────────────────────────────────────────────

# P1: API error rate > 5% (5xx responses)
resource "aws_cloudwatch_metric_alarm" "api_error_rate" {
  alarm_name          = "pilot-${var.environment}-api-error-rate"
  alarm_description   = "P1: API 5xx error rate > 5% for 5 minutes - potential service failure"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  threshold           = 5

  # Compare 5xx count as % of total requests
  metric_query {
    id          = "error_rate"
    expression  = "errors / requests * 100"
    label       = "Error Rate (%)"
    return_data = true
  }

  metric_query {
    id = "errors"
    metric {
      namespace   = "AWS/ApplicationELB"
      metric_name = "HTTPCode_Target_5XX_Count"
      period      = 300
      stat        = "Sum"
      dimensions  = { LoadBalancer = var.alb_arn_suffix }
    }
  }

  metric_query {
    id = "requests"
    metric {
      namespace   = "AWS/ApplicationELB"
      metric_name = "RequestCount"
      period      = 300
      stat        = "Sum"
      dimensions  = { LoadBalancer = var.alb_arn_suffix }
    }
  }

  alarm_actions      = [aws_sns_topic.alarms.arn]
  ok_actions         = [aws_sns_topic.alarms.arn]
  treat_missing_data = "notBreaching"

  tags = {
    Component      = "monitoring"
    CostAllocation = "security-monitoring"
    Severity       = "critical"
  }
}

# P1: API p95 latency > 2000ms
resource "aws_cloudwatch_metric_alarm" "api_p95_latency" {
  alarm_name          = "pilot-${var.environment}-api-p95-latency"
  alarm_description   = "P1: API p95 latency > 2000ms for 5 minutes - rollback trigger at 1s"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  threshold           = 2

  namespace          = "AWS/ApplicationELB"
  metric_name        = "TargetResponseTime"
  period             = 300
  extended_statistic = "p95" # percentile stats use extended_statistic, not statistic
  dimensions         = { LoadBalancer = var.alb_arn_suffix }

  alarm_actions      = [aws_sns_topic.alarms.arn]
  ok_actions         = [aws_sns_topic.alarms.arn]
  treat_missing_data = "notBreaching"

  tags = {
    Component      = "monitoring"
    CostAllocation = "security-monitoring"
    Severity       = "high"
  }
}

# P1: ALB unhealthy targets
resource "aws_cloudwatch_metric_alarm" "alb_unhealthy_hosts" {
  alarm_name          = "pilot-${var.environment}-alb-unhealthy-hosts"
  alarm_description   = "P1: ALB has unhealthy targets - immediate investigation required"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  threshold           = 0

  namespace   = "AWS/ApplicationELB"
  metric_name = "UnHealthyHostCount"
  period      = 60
  statistic   = "Maximum"
  dimensions  = { LoadBalancer = var.alb_arn_suffix }

  alarm_actions      = [aws_sns_topic.alarms.arn]
  ok_actions         = [aws_sns_topic.alarms.arn]
  treat_missing_data = "notBreaching"

  tags = {
    Component      = "monitoring"
    CostAllocation = "security-monitoring"
    Severity       = "critical"
  }
}

# ECS API CPU > 70% for 15 min
resource "aws_cloudwatch_metric_alarm" "ecs_api_cpu" {
  alarm_name          = "pilot-${var.environment}-ecs-api-cpu"
  alarm_description   = "High: ECS API CPU > 70% for 15 minutes - consider scaling"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  threshold           = 70

  namespace   = "AWS/ECS"
  metric_name = "CPUUtilization"
  period      = 300
  statistic   = "Average"
  dimensions = {
    ClusterName = var.ecs_cluster_name
    ServiceName = "pilot-api"
  }

  alarm_actions      = [aws_sns_topic.alarms.arn]
  ok_actions         = [aws_sns_topic.alarms.arn]
  treat_missing_data = "notBreaching"

  tags = {
    Component      = "monitoring"
    CostAllocation = "security-monitoring"
    Severity       = "high"
  }
}

# ECS API Memory > 80% for 15 min
resource "aws_cloudwatch_metric_alarm" "ecs_api_memory" {
  alarm_name          = "pilot-${var.environment}-ecs-api-memory"
  alarm_description   = "High: ECS API memory > 80% for 15 minutes - potential OOM risk"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  threshold           = 80

  namespace   = "AWS/ECS"
  metric_name = "MemoryUtilization"
  period      = 300
  statistic   = "Average"
  dimensions = {
    ClusterName = var.ecs_cluster_name
    ServiceName = "pilot-api"
  }

  alarm_actions      = [aws_sns_topic.alarms.arn]
  ok_actions         = [aws_sns_topic.alarms.arn]
  treat_missing_data = "notBreaching"

  tags = {
    Component      = "monitoring"
    CostAllocation = "security-monitoring"
    Severity       = "high"
  }
}

# ECS API Memory > 90% for 5 min — ESCALATION (approaching OOM, act immediately)
# Note: 70% and 75% warning alarms removed 2026-07-05 — pilot-api idles at 70-78%
# so those thresholds fired constantly in the normal operating range.
# Ladder: 80% for 15 min = investigate → 90% for 5 min = act immediately before OOM
resource "aws_cloudwatch_metric_alarm" "ecs_api_memory_critical_90" {
  alarm_name          = "pilot-${var.environment}-ecs-api-memory-critical-90"
  alarm_description   = "CRITICAL: ECS API memory > 90% for 5 minutes - approaching OOM, force-redeploy or scale immediately"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  threshold           = 90

  namespace   = "AWS/ECS"
  metric_name = "MemoryUtilization"
  period      = 300
  statistic   = "Average"
  dimensions = {
    ClusterName = var.ecs_cluster_name
    ServiceName = "pilot-api"
  }

  alarm_actions      = [aws_sns_topic.alarms.arn]
  ok_actions         = [aws_sns_topic.alarms.arn]
  treat_missing_data = "notBreaching"

  tags = {
    Component      = "monitoring"
    CostAllocation = "security-monitoring"
    Severity       = "critical"
  }
}

# RDS connections > 80 (max_connections = 100)
resource "aws_cloudwatch_metric_alarm" "rds_connections" {
  alarm_name          = "pilot-${var.environment}-rds-connections"
  alarm_description   = "High: RDS connections > 80 (max=100) - connection pool pressure"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  threshold           = 80

  namespace   = "AWS/RDS"
  metric_name = "DatabaseConnections"
  period      = 300
  statistic   = "Maximum"
  dimensions  = { DBInstanceIdentifier = var.rds_identifier }

  alarm_actions      = [aws_sns_topic.alarms.arn]
  ok_actions         = [aws_sns_topic.alarms.arn]
  treat_missing_data = "notBreaching"

  tags = {
    Component      = "monitoring"
    CostAllocation = "security-monitoring"
    Severity       = "high"
  }
}

# RDS CPU > 60% for 10 min
resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  alarm_name          = "pilot-${var.environment}-rds-cpu"
  alarm_description   = "Medium: RDS CPU > 60% for 10 minutes - review slow query log"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  threshold           = 60

  namespace   = "AWS/RDS"
  metric_name = "CPUUtilization"
  period      = 300
  statistic   = "Average"
  dimensions  = { DBInstanceIdentifier = var.rds_identifier }

  alarm_actions      = [aws_sns_topic.alarms.arn]
  ok_actions         = [aws_sns_topic.alarms.arn]
  treat_missing_data = "notBreaching"

  tags = {
    Component      = "monitoring"
    CostAllocation = "security-monitoring"
    Severity       = "medium"
  }
}

# RDS free storage < 5GB (5,368,709,120 bytes)
resource "aws_cloudwatch_metric_alarm" "rds_storage" {
  alarm_name          = "pilot-${var.environment}-rds-free-storage"
  alarm_description   = "High: RDS free storage < 5GB - autoscaling should trigger; verify storage capacity"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  threshold           = 5368709120 # 5GB in bytes

  namespace   = "AWS/RDS"
  metric_name = "FreeStorageSpace"
  period      = 300
  statistic   = "Minimum"
  dimensions  = { DBInstanceIdentifier = var.rds_identifier }

  alarm_actions      = [aws_sns_topic.alarms.arn]
  ok_actions         = [aws_sns_topic.alarms.arn]
  treat_missing_data = "notBreaching"

  tags = {
    Component      = "monitoring"
    CostAllocation = "security-monitoring"
    Severity       = "high"
  }
}

# Redis CPU > 60% for 10 min
resource "aws_cloudwatch_metric_alarm" "redis_cpu" {
  alarm_name          = "pilot-${var.environment}-redis-cpu"
  alarm_description   = "Medium: ElastiCache Redis CPU > 60% for 10 minutes"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  threshold           = 60

  namespace   = "AWS/ElastiCache"
  metric_name = "CPUUtilization"
  period      = 300
  statistic   = "Average"
  dimensions  = { CacheClusterId = var.elasticache_cluster_id }

  alarm_actions      = [aws_sns_topic.alarms.arn]
  ok_actions         = [aws_sns_topic.alarms.arn]
  treat_missing_data = "notBreaching"

  tags = {
    Component      = "monitoring"
    CostAllocation = "security-monitoring"
    Severity       = "medium"
  }
}

# GPU Instance StatusCheck failed (gated — only created when gpu_quota_approved=true)
resource "aws_cloudwatch_metric_alarm" "gpu_status_check" {
  count               = var.gpu_quota_approved ? 1 : 0
  alarm_name          = "pilot-${var.environment}-gpu-status-check"
  alarm_description   = "Critical: GPU EC2 instance StatusCheck failed - Whisper/Ollama may be down"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  threshold           = 0

  namespace   = "AWS/EC2"
  metric_name = "StatusCheckFailed"
  period      = 60
  statistic   = "Maximum"
  dimensions  = { InstanceId = var.gpu_instance_id }

  alarm_actions = [aws_sns_topic.alarms.arn]
  ok_actions    = [aws_sns_topic.alarms.arn]
  # notBreaching: EC2 StatusCheckFailed metric takes ~2 min to start publishing after
  # instance creation. 'breaching' causes false-alarm on first apply. Changed 2026-07-05.
  treat_missing_data = "notBreaching"

  tags = {
    Component      = "monitoring"
    CostAllocation = "security-monitoring"
    Severity       = "critical"
  }
}

# COGNITO-EMAIL-1: Custom Email Sender Lambda Errors alarm.
# This Lambda IS the auth email delivery path (signup/forgot/invite codes).
# If it fails, users get no verification code and no error — Cognito surfaces
# a clean failure, but the alarm ensures ops knows immediately.
# Rollback: detach the trigger (runbook §14.5) — Cognito falls back to
# COGNITO_DEFAULT sending instantly.
resource "aws_cloudwatch_metric_alarm" "custom_email_sender_errors" {
  alarm_name          = "pilot-${var.environment}-custom-email-sender-errors"
  alarm_description   = "Custom Email Sender failed — auth emails (signup/forgot/invite) are NOT being delivered; rollback = detach trigger, runbook §14.5"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  threshold           = 0

  namespace   = "AWS/Lambda"
  metric_name = "Errors"
  period      = 300
  statistic   = "Sum"
  dimensions = {
    FunctionName = "pilot-${var.environment}-custom-email-sender"
  }

  alarm_actions      = [aws_sns_topic.alarms.arn]
  ok_actions         = [aws_sns_topic.alarms.arn]
  treat_missing_data = "notBreaching"

  tags = {
    Component      = "monitoring"
    CostAllocation = "security-monitoring"
    Severity       = "critical"
  }
}

# ─── GuardDuty ────────────────────────────────────────────────────────────────

resource "aws_guardduty_detector" "pilot" {
  enable = true

  datasources {
    s3_logs {
      enable = true
    }
    kubernetes {
      audit_logs {
        enable = false # No Kubernetes in this architecture
      }
    }
    malware_protection {
      scan_ec2_instance_with_findings {
        ebs_volumes {
          enable = true # Scan GPU and bastion EBS volumes on threat detection
        }
      }
    }
  }

  tags = {
    Name           = "pilot-${var.environment}-guardduty"
    Component      = "monitoring"
    CostAllocation = "security-monitoring"
  }
}

# ─── Security Hub ─────────────────────────────────────────────────────────────

resource "aws_securityhub_account" "pilot" {}

resource "aws_securityhub_standards_subscription" "cis" {
  standards_arn = "arn:aws:securityhub:${var.aws_region}::standards/cis-aws-foundations-benchmark/v/1.4.0"
  depends_on    = [aws_securityhub_account.pilot]
}

resource "aws_securityhub_standards_subscription" "aws_foundational" {
  standards_arn = "arn:aws:securityhub:${var.aws_region}::standards/aws-foundational-security-best-practices/v/1.0.0"
  depends_on    = [aws_securityhub_account.pilot]

  timeouts {
    create = "10m"
  }
}

# ─── AWS Config: Required Tag Compliance Rule ─────────────────────────────────

resource "aws_config_configuration_recorder" "pilot" {
  name     = "pilot-${var.environment}-recorder"
  role_arn = aws_iam_role.config.arn

  recording_group {
    all_supported                 = true
    include_global_resource_types = true
  }
}

resource "aws_s3_bucket" "config" {
  bucket = "pilot-${var.environment}-config-logs-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name           = "pilot-${var.environment}-config-logs"
    Component      = "monitoring"
    CostAllocation = "security-monitoring"
    Backup         = "disabled"
  }

  lifecycle {
    # HIBERNATE-1: toggled off for teardown; restart restores true
    prevent_destroy = false
    # Ignore bucket name drift — account_id is "known after apply" during plan phase
    # causing spurious replace diff even though the name doesn't actually change
    ignore_changes = [bucket]
  }
}

# Versioning on config bucket — preserves compliance audit trail if objects are accidentally overwritten
resource "aws_s3_bucket_versioning" "config" {
  bucket = aws_s3_bucket.config.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "config" {
  bucket = aws_s3_bucket.config.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "config" {
  bucket = aws_s3_bucket.config.id
  policy = data.aws_iam_policy_document.config_s3.json
}

data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "config_s3" {
  statement {
    sid    = "AWSConfigBucketPermissionsCheck"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["config.amazonaws.com"]
    }
    actions   = ["s3:GetBucketAcl"]
    resources = [aws_s3_bucket.config.arn]
  }

  statement {
    sid    = "AWSConfigBucketDelivery"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["config.amazonaws.com"]
    }
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.config.arn}/AWSLogs/${data.aws_caller_identity.current.account_id}/Config/*"]
    condition {
      test     = "StringEquals"
      variable = "s3:x-amz-acl"
      values   = ["bucket-owner-full-control"]
    }
  }
}

resource "aws_config_delivery_channel" "pilot" {
  name           = "pilot-${var.environment}-delivery"
  s3_bucket_name = aws_s3_bucket.config.bucket
  depends_on     = [aws_config_configuration_recorder.pilot]
}

resource "aws_config_configuration_recorder_status" "pilot" {
  name       = aws_config_configuration_recorder.pilot.name
  is_enabled = true
  depends_on = [aws_config_delivery_channel.pilot]
}

resource "aws_iam_role" "config" {
  name = "pilot-${var.environment}-config-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "config.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "config" {
  role       = aws_iam_role.config.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWS_ConfigRole"
}

# Tag compliance: enforce 5 mandatory tags on key resource types
resource "aws_config_config_rule" "required_tags" {
  name = "pilot-required-tags"

  source {
    owner             = "AWS"
    source_identifier = "REQUIRED_TAGS"
  }

  input_parameters = jsonencode({
    tag1Key = "Project"
    tag2Key = "Environment"
    tag3Key = "Owner"
    tag4Key = "Component"
    tag5Key = "CostAllocation"
  })

  scope {
    compliance_resource_types = [
      "AWS::EC2::Instance",
      "AWS::RDS::DBInstance",
      "AWS::ElastiCache::CacheCluster",
      "AWS::ECS::Service",
      "AWS::S3::Bucket",
      "AWS::ElasticLoadBalancingV2::LoadBalancer",
    ]
  }

  depends_on = [aws_config_configuration_recorder_status.pilot]

  tags = {
    Component      = "monitoring"
    CostAllocation = "security-monitoring"
  }
}

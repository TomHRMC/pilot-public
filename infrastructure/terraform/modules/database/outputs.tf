output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint hostname"
  value       = aws_db_instance.postgres.address
  sensitive   = true
}

output "rds_identifier" {
  description = "RDS instance identifier — used in CloudWatch alarms"
  value       = aws_db_instance.postgres.id
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint hostname"
  value       = aws_elasticache_cluster.redis.cache_nodes[0].address
  sensitive   = true
}

output "elasticache_cluster_id" {
  description = "ElastiCache cluster ID — used in CloudWatch alarms"
  value       = aws_elasticache_cluster.redis.cluster_id
}

output "db_password" {
  description = "Generated RDS master password — stored in Secrets Manager, not for direct use"
  value       = random_password.db_password.result
  sensitive   = true
}

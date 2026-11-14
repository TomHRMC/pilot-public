# ─── RDS PostgreSQL 17 + pgvector ─────────────────────────────────────────────

resource "random_password" "db_password" {
  length           = 32
  special          = true
  override_special = "!#$%^&*()-_=+[]{}:?"
}

resource "aws_db_subnet_group" "private" {
  name       = "pilot-${var.environment}-db-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name           = "pilot-${var.environment}-db-subnet-group"
    Component      = "data-layer"
    CostAllocation = "data-layer"
  }
}

resource "aws_db_parameter_group" "postgres17" {
  name   = "pilot-${var.environment}-postgres17"
  family = "postgres17"

  # Tuned for db.t4g.micro: 1GB RAM, 2 vCPU
  # Static params (require pending-reboot): max_connections, shared_buffers
  # Dynamic params (immediate ok): effective_cache_size, random_page_cost, work_mem
  parameter {
    name         = "max_connections"
    value        = "100"
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "shared_buffers"
    value        = "131072" # 128MB in 8KB pages (IOPS-efficient for t4g.micro)
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "effective_cache_size"
    value        = "393216" # 384MB — conservative for 1GB RAM instance
    apply_method = "immediate"
  }

  parameter {
    name         = "random_page_cost"
    value        = "1.1" # Optimized for SSD-backed RDS
    apply_method = "immediate"
  }

  parameter {
    name         = "work_mem"
    value        = "4096" # 4MB per operation — safe for 100 connections
    apply_method = "immediate"
  }

  parameter {
    name         = "log_min_duration_statement"
    value        = "1000" # Log queries taking > 1 second
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "log_connections"
    value        = "1"
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "log_disconnections"
    value        = "1"
    apply_method = "pending-reboot"
  }

  tags = {
    Name           = "pilot-${var.environment}-postgres17"
    Component      = "data-layer"
    CostAllocation = "data-layer"
  }
}

resource "aws_db_instance" "postgres" {
  identifier            = "pilot-${var.environment}"
  engine                = "postgres"
  engine_version        = "17" # AWS RDS supports pg17; fallback to 16.x if not yet available
  instance_class        = var.db_instance_class
  allocated_storage     = 20  # GB; autoscaling handles growth
  max_allocated_storage = 100 # Autoscaling ceiling at 100GB

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db_password.result

  multi_az               = true # Production-spec design target (99.9% availability)
  db_subnet_group_name   = aws_db_subnet_group.private.name
  vpc_security_group_ids = [var.sg_rds_id]
  parameter_group_name   = aws_db_parameter_group.postgres17.name

  storage_encrypted = true
  kms_key_id        = var.kms_key_arn
  storage_type      = "gp2"

  # 28-day automated backups; window 3–4 AM Eastern (07:00–08:00 UTC)
  backup_retention_period = 28
  backup_window           = "07:00-08:00"
  maintenance_window      = "sun:08:00-sun:09:00" # 4–5 AM Eastern Sunday — format: ddd:hh24:mi-ddd:hh24:mi

  performance_insights_enabled          = true
  performance_insights_retention_period = 7 # Free 7-day retention tier

  deletion_protection       = false # HIBERNATE-1: toggled off for teardown; restart restores true
  skip_final_snapshot       = true  # HIBERNATE-1: Tom's ruling — dbbackups/ pair is the backup; avoids fixed-name collision
  final_snapshot_identifier = "pilot-${var.environment}-final-snapshot"

  # pgvector extension: enable via first Alembic migration
  # Run: CREATE EXTENSION IF NOT EXISTS vector;
  # After that, HNSW indexes can be created on embedding columns

  tags = {
    Name               = "pilot-${var.environment}-postgres"
    Component          = "data-layer"
    CostAllocation     = "data-layer"
    DataClassification = "sensitive"
    Backup             = "enabled"
  }
}

# Store DB credentials in Secrets Manager (security module creates the secret shell;
# database module populates the value after RDS is created)
resource "aws_secretsmanager_secret_version" "db" {
  secret_id = var.secret_db_arn
  secret_string = jsonencode({
    username = var.db_username
    password = random_password.db_password.result
    host     = aws_db_instance.postgres.address
    port     = 5432
    dbname   = var.db_name
    url      = "postgresql://${var.db_username}:${random_password.db_password.result}@${aws_db_instance.postgres.address}:5432/${var.db_name}"
  })
}

# ─── ElastiCache Redis 7 ──────────────────────────────────────────────────────

resource "aws_elasticache_subnet_group" "private" {
  name       = "pilot-${var.environment}-redis-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name           = "pilot-${var.environment}-redis-subnet-group"
    Component      = "data-layer"
    CostAllocation = "data-layer"
  }
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id      = "pilot-${var.environment}"
  engine          = "redis"
  engine_version  = "7.1"
  node_type       = "cache.t4g.micro"
  num_cache_nodes = 1
  port            = 6379

  subnet_group_name  = aws_elasticache_subnet_group.private.name
  security_group_ids = [var.sg_redis_id]

  # at_rest_encryption_enabled is NOT supported on aws_elasticache_cluster; it requires an
  # aws_elasticache_replication_group (Phase 2 upgrade path)
  # As built, this single-node cluster has no at-rest or in-transit encryption and no
  # auth token (Known Limitations #24); the replication group is the Phase 2 fix.

  # Note: transit_encryption_enabled requires TLS in connection strings
  # rediss://host:6379/db — requires app config update; disabled for MVP simplicity
  # Enable in Phase 2 security hardening
  # transit_encryption_enabled = true

  # 3 logical databases (DB 0/1/2) on this single node:
  # DB 0: rate limiting (SlowAPI token buckets)
  # DB 1: Celery task broker
  # DB 2: Celery result backend
  #
  # Connection strings:
  # REDIS_URL         = redis://<host>:6379/0  (rate limiting)
  # CELERY_BROKER_URL = redis://<host>:6379/1
  # CELERY_RESULT     = redis://<host>:6379/2

  apply_immediately = false

  tags = {
    Name           = "pilot-${var.environment}-redis"
    Component      = "data-layer"
    CostAllocation = "data-layer"
    Backup         = "disabled"
  }
}

# Store Redis connection info in Secrets Manager
resource "aws_secretsmanager_secret_version" "redis" {
  secret_id = var.secret_redis_arn
  secret_string = jsonencode({
    host       = aws_elasticache_cluster.redis.cache_nodes[0].address
    port       = 6379
    broker_url = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379/1"
    result_url = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379/2"
    rate_url   = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379/0"
  })
}

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║ SUPERSEDED — kept for history. This is the earlier root module from the     ║
# ║ App Runner design (pre-ADR-0001). It references module outputs that no      ║
# ║ longer exist and will NOT validate. The active configuration is             ║
# ║ environments/production/ (self-contained; same modules).                    ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# ─── Pilot for Trades — Root Module ───────────────────────────────────────────
# All resources deploy into the HotRMC AWS account (000000000000).
# Run terraform commands from: infrastructure/terraform/environments/production/
# This root module is composed of modules called by environments/production/main.tf.

# ─── Networking ───────────────────────────────────────────────────────────────
module "networking" {
  source = "./modules/networking"

  environment          = var.environment
  vpc_cidr             = var.vpc_cidr
  admin_allowed_ips    = var.admin_allowed_ips
  tom_admin_public_key = var.tom_admin_public_key
}

# ─── Security (KMS, Secrets Manager, IAM, Cognito) ────────────────────────────
module "security" {
  source = "./modules/security"

  environment           = var.environment
  aws_region            = var.aws_region
  account_id            = var.account_id
  domain_name           = var.domain_name
  github_repo           = var.github_repo
  cognito_user_pool_id  = var.cognito_user_pool_id
  cognito_app_client_id = var.cognito_app_client_id

  # Networking dependencies
  vpc_id             = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids
  sg_lambda_id       = module.networking.sg_lambda_id

  depends_on = [module.networking]
}

# ─── Database (RDS PostgreSQL + ElastiCache Redis) ────────────────────────────
module "database" {
  source = "./modules/database"

  environment       = var.environment
  db_instance_class = var.db_instance_class
  db_name           = var.db_name
  db_username       = var.db_username
  kms_key_arn       = module.security.kms_key_arn

  # Networking dependencies
  private_subnet_ids = module.networking.private_subnet_ids
  sg_rds_id          = module.networking.sg_rds_id
  sg_redis_id        = module.networking.sg_redis_id

  depends_on = [module.networking, module.security]
}

# ─── Storage (S3 Buckets) ─────────────────────────────────────────────────────
module "storage" {
  source = "./modules/storage"

  environment = var.environment
  kms_key_arn = module.security.kms_key_arn
  account_id  = var.account_id

  depends_on = [module.security]
}

# ─── Compute (ECS, EC2 GPU, ECR) ──────────────────────────────────────────────
module "compute" {
  source = "./modules/compute"

  environment              = var.environment
  aws_region               = var.aws_region
  account_id               = var.account_id
  domain_name              = var.domain_name
  gpu_ami_id               = var.gpu_ami_id
  ecs_api_desired_count    = var.ecs_api_desired_count
  ecs_worker_desired_count = var.ecs_worker_desired_count

  # Networking dependencies
  vpc_id             = module.networking.vpc_id
  public_subnet_ids  = module.networking.public_subnet_ids
  private_subnet_ids = module.networking.private_subnet_ids
  sg_alb_id          = module.networking.sg_alb_id
  sg_ecs_api_id      = module.networking.sg_ecs_api_id
  sg_gpu_id          = module.networking.sg_gpu_id
  bastion_key_name   = module.networking.bastion_key_name

  # Security dependencies
  kms_key_arn            = module.security.kms_key_arn
  ecs_task_role_arn      = module.security.ecs_task_role_arn
  ecs_execution_role_arn = module.security.ecs_execution_role_arn
  app_runner_role_arn    = module.security.app_runner_role_arn
  acm_certificate_arn    = module.security.acm_certificate_arn
  cognito_user_pool_id   = var.cognito_user_pool_id
  cognito_app_client_id  = var.cognito_app_client_id

  # Secrets Manager ARNs for ECS task injection
  secret_db_arn          = module.security.secret_db_arn
  secret_sendgrid_arn    = module.security.secret_sendgrid_arn
  secret_telnyx_arn      = module.security.secret_telnyx_arn
  secret_stripe_arn      = module.security.secret_stripe_arn
  secret_quickbooks_arn  = module.security.secret_quickbooks_arn
  secret_encryption_arn  = module.security.secret_encryption_arn
  secret_cognito_arn     = module.security.secret_cognito_arn
  secret_google_maps_arn = module.security.secret_google_maps_arn
  secret_redis_arn       = module.security.secret_redis_arn

  depends_on = [module.networking, module.security, module.database]
}

# ─── Monitoring (CloudWatch, GuardDuty, Security Hub) ────────────────────────
module "monitoring" {
  source = "./modules/monitoring"

  environment                   = var.environment
  aws_region                    = var.aws_region
  alarm_email                   = var.alarm_email
  cloudwatch_log_retention_days = var.cloudwatch_log_retention_days

  # Compute dependencies for alarm targets
  alb_arn_suffix         = module.compute.alb_arn_suffix
  ecs_cluster_name       = module.compute.ecs_cluster_name
  rds_identifier         = module.database.rds_identifier
  elasticache_cluster_id = module.database.elasticache_cluster_id
  gpu_instance_id        = module.compute.gpu_instance_id

  depends_on = [module.compute, module.database]
}

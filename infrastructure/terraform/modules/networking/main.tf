# ─── VPC ──────────────────────────────────────────────────────────────────────

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name           = "pilot-${var.environment}-vpc"
    Component      = "networking"
    CostAllocation = "networking"
  }
}

# ─── Subnets ──────────────────────────────────────────────────────────────────

resource "aws_subnet" "public_a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "us-east-1a"
  map_public_ip_on_launch = false

  tags = {
    Name           = "pilot-${var.environment}-public-a"
    Component      = "networking"
    CostAllocation = "networking"
    Tier           = "public"
  }
}

resource "aws_subnet" "public_b" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "us-east-1b"
  map_public_ip_on_launch = false

  tags = {
    Name           = "pilot-${var.environment}-public-b"
    Component      = "networking"
    CostAllocation = "networking"
    Tier           = "public"
  }
}

resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.10.0/24"
  availability_zone = "us-east-1a"

  tags = {
    Name           = "pilot-${var.environment}-private-a"
    Component      = "networking"
    CostAllocation = "networking"
    Tier           = "private"
  }
}

resource "aws_subnet" "private_b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.11.0/24"
  availability_zone = "us-east-1b"

  tags = {
    Name           = "pilot-${var.environment}-private-b"
    Component      = "networking"
    CostAllocation = "networking"
    Tier           = "private"
  }
}

# ─── Internet Gateway ─────────────────────────────────────────────────────────

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name           = "pilot-${var.environment}-igw"
    Component      = "networking"
    CostAllocation = "networking"
  }
}

# ─── NAT Gateway (Single AZ — saves ~$32/mo vs Multi-AZ) ─────────────────────

resource "aws_eip" "nat" {
  domain = "vpc"

  tags = {
    Name           = "pilot-${var.environment}-nat-eip"
    Component      = "networking"
    CostAllocation = "networking"
  }

  depends_on = [aws_internet_gateway.main]
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public_a.id

  tags = {
    Name           = "pilot-${var.environment}-nat"
    Component      = "networking"
    CostAllocation = "networking"
  }

  depends_on = [aws_internet_gateway.main]
}

# ─── Route Tables ─────────────────────────────────────────────────────────────

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name           = "pilot-${var.environment}-rt-public"
    Component      = "networking"
    CostAllocation = "networking"
  }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }

  tags = {
    Name           = "pilot-${var.environment}-rt-private"
    Component      = "networking"
    CostAllocation = "networking"
  }
}

resource "aws_route_table_association" "public_a" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "public_b" {
  subnet_id      = aws_subnet.public_b.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private_a" {
  subnet_id      = aws_subnet.private_a.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_b" {
  subnet_id      = aws_subnet.private_b.id
  route_table_id = aws_route_table.private.id
}

# ─── VPC Endpoints ────────────────────────────────────────────────────────────

# S3 Gateway endpoint — free; no NAT Gateway charges for S3 traffic from private subnets
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.us-east-1.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]

  tags = {
    Name           = "pilot-${var.environment}-vpce-s3"
    Component      = "networking"
    CostAllocation = "networking"
  }
}

# Secrets Manager interface endpoint — ~$7/mo; eliminates NAT charges for secret retrieval
resource "aws_vpc_endpoint" "secretsmanager" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.us-east-1.secretsmanager"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [aws_subnet.private_a.id]
  security_group_ids  = [aws_security_group.sg_vpc_endpoint.id]
  private_dns_enabled = true

  tags = {
    Name           = "pilot-${var.environment}-vpce-secretsmanager"
    Component      = "networking"
    CostAllocation = "networking"
  }
}

# ─── Security Groups ──────────────────────────────────────────────────────────

# ALB — internet-facing; accepts 443 + 80
resource "aws_security_group" "sg_alb" {
  name        = "pilot-${var.environment}-sg-alb"
  description = "ALB - allows HTTPS/HTTP from internet"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTPS from internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP from internet (redirects to HTTPS)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name           = "pilot-${var.environment}-sg-alb"
    Component      = "networking"
    CostAllocation = "networking"
  }
}

# ECS API tasks — only accessible from ALB
resource "aws_security_group" "sg_ecs_api" {
  name        = "pilot-${var.environment}-sg-ecs-api"
  description = "ECS API tasks - allows port 8000 from ALB only"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "FastAPI port from ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.sg_alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name           = "pilot-${var.environment}-sg-ecs-api"
    Component      = "networking"
    CostAllocation = "networking"
  }
}

# RDS PostgreSQL — from ECS API, bastion, and the Post-Confirmation Lambda
# NOTE: description is immutable in AWS — do NOT change it or Terraform will
# destroy+recreate the SG (detaching it from the live RDS instance).
resource "aws_security_group" "sg_rds" {
  name        = "pilot-${var.environment}-sg-rds"
  description = "RDS PostgreSQL - allows port 5432 from ECS and bastion only"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL from ECS API tasks"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.sg_ecs_api.id]
  }

  ingress {
    description     = "PostgreSQL from bastion (SSH tunnel)"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.sg_bastion.id]
  }

  # SIGNUP-GA-1: Post-Confirmation Lambda writes tenant+user rows directly to
  # RDS on Cognito confirmation. Was a separate aws_security_group_rule which
  # conflicted with these inline blocks (Terraform inline-vs-separate footgun).
  ingress {
    description     = "PostgreSQL from Cognito post-confirmation Lambda"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.sg_lambda.id]
  }

  tags = {
    Name           = "pilot-${var.environment}-sg-rds"
    Component      = "networking"
    CostAllocation = "networking"
  }
}

# ElastiCache Redis — only from ECS API and bastion
resource "aws_security_group" "sg_redis" {
  name        = "pilot-${var.environment}-sg-redis"
  description = "ElastiCache Redis - allows port 6379 from ECS and bastion only"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Redis from ECS API tasks"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.sg_ecs_api.id]
  }

  ingress {
    description     = "Redis from bastion (SSH tunnel)"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.sg_bastion.id]
  }

  # PLATFORM-SMS-B2 (ADR-0013 / Pathway C): the Post-Authentication Lambda
  # enqueues the new-device alert task directly to the Redis broker via a
  # minimal Celery producer (kombu transport). This is the only networking
  # change — the RDS SG already allows 5432 from sg_lambda.
  ingress {
    description     = "Redis from Cognito Lambdas (post-authentication broker enqueue)"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.sg_lambda.id]
  }

  tags = {
    Name           = "pilot-${var.environment}-sg-redis"
    Component      = "networking"
    CostAllocation = "networking"
  }
}

# GPU instance — Whisper + Ollama ports from ECS, SSH from bastion
resource "aws_security_group" "sg_gpu" {
  name        = "pilot-${var.environment}-sg-gpu"
  description = "GPU EC2 - Whisper (8080) + Ollama (11434) from ECS; SSH from bastion"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Whisper API from ECS API tasks"
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.sg_ecs_api.id]
  }

  ingress {
    description     = "Ollama API from ECS API tasks"
    from_port       = 11434
    to_port         = 11434
    protocol        = "tcp"
    security_groups = [aws_security_group.sg_ecs_api.id]
  }

  ingress {
    description     = "SSH from bastion (proxy jump)"
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [aws_security_group.sg_bastion.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name           = "pilot-${var.environment}-sg-gpu"
    Component      = "networking"
    CostAllocation = "networking"
  }
}

# Bastion host — SSH from Tom's known IPs
resource "aws_security_group" "sg_bastion" {
  name        = "pilot-${var.environment}-sg-bastion"
  description = "Bastion host - SSH from admin IPs only"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name           = "pilot-${var.environment}-sg-bastion"
    Component      = "networking"
    CostAllocation = "networking"
  }
}

# Multi-IP bastion SSH ingress rule — one rule per IP in admin_allowed_ips list
resource "aws_security_group_rule" "bastion_ssh_ingress" {
  for_each          = toset(var.admin_allowed_ips)
  type              = "ingress"
  from_port         = 22
  to_port           = 22
  protocol          = "tcp"
  cidr_blocks       = ["${each.value}/32"]
  security_group_id = aws_security_group.sg_bastion.id
  description       = "SSH access from admin IP: ${each.value}"
}

# Lambda — no inbound; all outbound (needs VPC egress for RDS access)
resource "aws_security_group" "sg_lambda" {
  name        = "pilot-${var.environment}-sg-lambda"
  description = "Cognito post-confirmation Lambda - no inbound; VPC egress for RDS"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name           = "pilot-${var.environment}-sg-lambda"
    Component      = "networking"
    CostAllocation = "networking"
  }
}

# NOTE: The Lambda→RDS ingress rule was previously a separate
# aws_security_group_rule.rds_from_lambda resource, which conflicted with the
# inline ingress blocks on sg_rds (Terraform inline-vs-separate footgun — the
# inline blocks are authoritative and would delete the separate rule on apply).
# It is now an inline ingress block on sg_rds (see above). The separate resource
# was removed from config + state (terraform state rm) as part of SIGNUP-GA-1.

# VPC Endpoint security group — allows HTTPS from private subnets
resource "aws_security_group" "sg_vpc_endpoint" {
  name        = "pilot-${var.environment}-sg-vpce"
  description = "VPC Interface Endpoints - HTTPS from private subnets"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTPS from private subnets"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.10.0/24", "10.0.11.0/24"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name           = "pilot-${var.environment}-sg-vpce"
    Component      = "networking"
    CostAllocation = "networking"
  }
}

# ─── Bastion Host ─────────────────────────────────────────────────────────────

# SSH key pair using Tom's confirmed ed25519 public key
resource "aws_key_pair" "tom_admin" {
  key_name   = "pilot-admin-key"
  public_key = var.tom_admin_public_key

  tags = {
    Name           = "pilot-admin-key"
    Component      = "networking"
    CostAllocation = "networking"
  }
}

# Latest Amazon Linux 2023 AMI for ARM (t4g.nano)
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-arm64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_eip" "bastion" {
  domain = "vpc"

  tags = {
    Name           = "pilot-${var.environment}-bastion-eip"
    Component      = "networking"
    CostAllocation = "networking"
  }
}

resource "aws_instance" "bastion" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = "t4g.nano" # ~$3/month ARM; 512MB RAM
  subnet_id              = aws_subnet.public_a.id
  vpc_security_group_ids = [aws_security_group.sg_bastion.id]
  key_name               = aws_key_pair.tom_admin.key_name

  associate_public_ip_address = true

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 30 # Amazon Linux 2023 AMI requires >= 30GB (snapshot size)
    encrypted             = true
    delete_on_termination = true
  }

  tags = {
    Name           = "pilot-${var.environment}-bastion"
    Component      = "networking"
    CostAllocation = "networking"
    Backup         = "disabled"
  }

  lifecycle {
    ignore_changes = [ami] # Don't replace bastion on every AMI update
  }
}

resource "aws_eip_association" "bastion" {
  instance_id   = aws_instance.bastion.id
  allocation_id = aws_eip.bastion.id
}

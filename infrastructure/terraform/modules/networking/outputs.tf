output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs [us-east-1a, us-east-1b]"
  value       = [aws_subnet.public_a.id, aws_subnet.public_b.id]
}

output "private_subnet_ids" {
  description = "Private subnet IDs [us-east-1a, us-east-1b]"
  value       = [aws_subnet.private_a.id, aws_subnet.private_b.id]
}

output "sg_alb_id" {
  description = "ALB security group ID"
  value       = aws_security_group.sg_alb.id
}

output "sg_ecs_api_id" {
  description = "ECS API tasks security group ID"
  value       = aws_security_group.sg_ecs_api.id
}

output "sg_rds_id" {
  description = "RDS PostgreSQL security group ID"
  value       = aws_security_group.sg_rds.id
}

output "sg_redis_id" {
  description = "ElastiCache Redis security group ID"
  value       = aws_security_group.sg_redis.id
}

output "sg_gpu_id" {
  description = "GPU EC2 instance security group ID"
  value       = aws_security_group.sg_gpu.id
}

output "sg_bastion_id" {
  description = "Bastion host security group ID"
  value       = aws_security_group.sg_bastion.id
}

output "sg_lambda_id" {
  description = "Lambda security group ID"
  value       = aws_security_group.sg_lambda.id
}

output "bastion_public_ip" {
  description = "Bastion host static Elastic IP — set as HostName in ~/.ssh/config for pilot-bastion"
  value       = aws_eip.bastion.public_ip
}

output "nat_gateway_eip" {
  description = "NAT Gateway Elastic IP — add to Google Maps API key IP allowlist"
  value       = aws_eip.nat.public_ip
}

output "bastion_key_name" {
  description = "EC2 key pair name for the bastion and GPU instances"
  value       = aws_key_pair.tom_admin.key_name
}

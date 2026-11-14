variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "admin_allowed_ips" {
  description = "List of admin public IPs for bastion SSH access"
  type        = list(string)
}

variable "tom_admin_public_key" {
  description = "Tom's SSH public key for bastion EC2 key pair"
  type        = string
}

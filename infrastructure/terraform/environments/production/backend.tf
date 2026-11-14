terraform {
  backend "s3" {
    bucket       = "pilot-terraform-state-000000000000"
    key          = "production/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
    # Note: dynamodb_table is deprecated in Terraform 1.10+; use_lockfile uses S3 native locking
    # DynamoDB table pilot-terraform-locks was created but is no longer needed

    # S3 bucket name includes account ID (000000000000) to guarantee global uniqueness
    # Plain "pilot-terraform-state" was already taken by another AWS account
    # S3 bucket names are globally unique across ALL AWS accounts worldwide
    # Prevents concurrent terraform applies from corrupting state
  }
}

# terraform/backend.tf

terraform {
  backend "s3" {
    bucket         = "llmops-rag-terraform-state" # Replace with your bucket name
    key            = "llmops-rag/terraform.tfstate"
    region         = "ap-southeast-2"
    encrypt        = true
    dynamodb_table = "llmops-rag-terraform-state-lock" # We'll create this later
  }

  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "ap-southeast-2"

  default_tags {
    tags = {
      Project     = "LLMOps"
      ManagedBy   = "Terraform"
      Environment = "dev"
    }
  }
}

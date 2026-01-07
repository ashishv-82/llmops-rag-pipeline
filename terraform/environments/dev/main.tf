# terraform/environments/dev/main.tf

terraform {
  required_version = ">= 1.7.0"

  backend "s3" {
    bucket         = "llmops-rag-terraform-state"
    key            = "dev/terraform.tfstate"
    region         = "ap-southeast-2"
    encrypt        = true
    dynamodb_table = "llmops-rag-terraform-state-lock"
  }
}

module "documents_bucket" {
  source = "../../modules/s3"

  bucket_name      = "llmops-rag-documents-dev"
  environment      = "dev"
  enable_lifecycle = true
}

module "embeddings_bucket" {
  source = "../../modules/s3"

  bucket_name      = "llmops-rag-embeddings-dev"
  environment      = "dev"
  enable_lifecycle = false # No lifecycle needed for short-lived feature store
}

# ECR Repository for Docker images
module "ecr" {
  source = "../../modules/ecr"

  repository_name      = "llmops-rag-api"
  image_tag_mutability = "MUTABLE"
  scan_on_push         = true
  encryption_type      = "AES256"

  tags = {
    Environment = "dev"
    Project     = "llmops-rag-pipeline"
    ManagedBy   = "terraform"
  }
}

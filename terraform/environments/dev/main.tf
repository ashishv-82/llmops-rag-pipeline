# terraform/environments/dev/main.tf

terraform {
  required_version = ">= 1.7.0"
}

module "documents_bucket" {
  source = "../../modules/s3"

  bucket_name      = "llmops-rag-documents-dev-av" # Replace with your bucket name
  environment      = "dev"
  enable_lifecycle = true
}

output "documents_bucket_name" {
  value = module.documents_bucket.bucket_name
}

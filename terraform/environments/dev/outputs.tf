output "documents_bucket_name" {
  description = "Name of the documents S3 bucket"
  value       = module.documents_bucket.bucket_name
}

output "embeddings_bucket_name" {
  description = "Name of the embeddings S3 bucket"
  value       = module.embeddings_bucket.bucket_name
}

output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = module.ecr.repository_url
}

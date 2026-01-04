output "documents_bucket_name" {
  description = "Name of the created documents bucket"
  value       = module.documents_bucket.bucket_name
}

output "embeddings_bucket_name" {
  description = "Name of the created embeddings bucket"
  value       = module.embeddings_bucket.bucket_name
}


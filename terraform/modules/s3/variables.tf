# terraform/modules/s3/variables.tf
# Input variables - defines module interface

variable "bucket_name" {
  description = "Name of the S3 bucket"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "enable_lifecycle" {
  description = "Enable lifecycle policies for cost optimization"
  type        = bool
  default     = true
}

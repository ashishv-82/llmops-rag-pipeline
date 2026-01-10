terraform {
  required_version = ">= 1.7.0"

  backend "s3" {
    bucket         = "llmops-rag-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "ap-southeast-2"
    encrypt        = true
    dynamodb_table = "llmops-rag-terraform-state-lock"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
  }
}

provider "aws" {
  region = "ap-southeast-2"

  default_tags {
    tags = {
      Project     = "llmops-rag-pipeline"
      Environment = "prod"
      ManagedBy   = "terraform"
      CostCenter  = "Engineering"
    }
  }
}

# --- Networking ---
module "vpc" {
  source = "../../modules/vpc"

  project_name = "llmops-rag-pipeline"
  environment  = "prod"
  cluster_name = "llmops-rag-cluster"
}

# --- S3 Buckets ---
module "documents_bucket" {
  source = "../../modules/s3"

  bucket_name      = "llmops-rag-documents-prod"
  environment      = "prod"
  enable_lifecycle = true
}

module "embeddings_bucket" {
  source = "../../modules/s3"

  bucket_name      = "llmops-rag-embeddings-prod"
  environment      = "prod"
  enable_lifecycle = false
}

# --- ECR ---
module "ecr" {
  source = "../../modules/ecr"

  repository_name      = "llmops-rag-api"
  image_tag_mutability = "MUTABLE"
  scan_on_push         = true
  encryption_type      = "AES256"

  tags = {
    Environment = "prod"
  }
}

module "ecr_frontend" {
  source = "../../modules/ecr"

  repository_name      = "llmops-rag-frontend"
  image_tag_mutability = "MUTABLE"
  scan_on_push         = true
  encryption_type      = "AES256"

  tags = {
    Environment = "prod"
  }
}

# --- EKS Cluster ---
module "eks" {
  source = "../../modules/eks"

  cluster_name       = "llmops-rag-cluster"
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
}

# --- IAM Roles for Service Accounts (IRSA) ---

# Role for RAG API (S3 access)
module "rag_api_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.30"

  role_name = "rag-api-prod"

  role_policy_arns = {
    # Custom policy for S3 access
    s3_access = aws_iam_policy.s3_access.arn
    # Bedrock access (if using Bedrock)
    bedrock = aws_iam_policy.bedrock_access.arn
  }

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["prod:rag-api"]
    }
  }
}

# Role for External Secrets Operator
module "external_secrets_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.30"

  role_name = "external-secrets-prod"

  attach_external_secrets_policy = true

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:external-secrets"]
    }
  }
}

# --- IAM Policies ---

resource "aws_iam_policy" "s3_access" {
  name        = "rag-s3-access-prod"
  description = "Access to documents bucket"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          module.documents_bucket.bucket_arn,
          "${module.documents_bucket.bucket_arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_policy" "bedrock_access" {
  name        = "rag-bedrock-access-prod"
  description = "Access to Bedrock models"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "*" # Restrict to specific models in real prod
      }
    ]
  })
}

# --- Monitoring ---
module "monitoring" {
  source = "../../modules/monitoring"

  namespace        = "monitoring"
  grafana_password = "admin" # Change for real environments!
}

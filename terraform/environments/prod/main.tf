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

provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)

  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
    command     = "aws"
  }
}

provider "helm" {
  kubernetes {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)

    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
      command     = "aws"
    }
  }
}

# --- Cluster Access Fix ---
resource "aws_eks_access_entry" "admin_access" {
  cluster_name  = module.eks.cluster_name
  principal_arn = "arn:aws:iam::152141418178:user/admin-user"
  type          = "STANDARD"

  depends_on = [module.eks]
}

resource "aws_eks_access_policy_association" "admin_policy" {
  cluster_name  = module.eks.cluster_name
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
  principal_arn = aws_eks_access_entry.admin_access.principal_arn

  access_scope {
    type = "cluster"
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

# --- Persistent Storage for ChromaDB ---

data "aws_region" "current" {}

resource "aws_ebs_volume" "chromadb_data" {
  availability_zone = "${data.aws_region.current.name}a"
  size              = 10
  type              = "gp3"

  tags = {
    Name        = "chromadb-persistent-storage"
    Project     = "llmops-rag-pipeline"
    Environment = "prod"
  }

  lifecycle {
    prevent_destroy = true
  }
}

output "chromadb_volume_id" {
  value       = aws_ebs_volume.chromadb_data.id
  description = "The ID of the EBS volume for ChromaDB"
}

# --- Monitoring ---
module "monitoring" {
  source = "../../modules/monitoring"

  namespace        = "monitoring"
  grafana_password = "admin" # Change for real environments!
}

resource "kubernetes_namespace" "envs" {
  for_each = toset(["dev", "staging", "prod"])

  metadata {
    name = each.key
    labels = {
      environment = each.key
      managed_by  = "terraform"
    }
  }

  depends_on = [module.eks, aws_eks_access_entry.admin_access]
}

# --- External Secrets Operator ---
resource "helm_release" "external_secrets" {
  name       = "external-secrets"
  repository = "https://charts.external-secrets.io"
  chart      = "external-secrets"
  version    = "0.9.19" # Fixed version for K8s 1.29 compatibility
  namespace  = "kube-system"

  set {
    name  = "installCRDs"
    value = "true"
  }

  set {
    name  = "serviceAccount.annotations.eks\\.amazonaws\\.com/role-arn"
    value = module.external_secrets_irsa.iam_role_arn
  }

  depends_on = [module.eks]
}

# --- AWS Load Balancer Controller ---
module "aws_load_balancer_controller_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.30"

  role_name = "aws-load-balancer-controller-prod"

  attach_load_balancer_controller_policy = true

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:aws-load-balancer-controller"]
    }
  }
}

resource "helm_release" "aws_load_balancer_controller" {
  name       = "aws-load-balancer-controller"
  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"
  namespace  = "kube-system"
  version    = "1.6.2"

  set {
    name  = "clusterName"
    value = module.eks.cluster_name
  }

  set {
    name  = "serviceAccount.create"
    value = "true"
  }

  set {
    name  = "serviceAccount.name"
    value = "aws-load-balancer-controller"
  }

  set {
    name  = "serviceAccount.annotations.eks\\.amazonaws\\.com/role-arn"
    value = module.aws_load_balancer_controller_irsa.iam_role_arn
  }

  depends_on = [module.eks]
}

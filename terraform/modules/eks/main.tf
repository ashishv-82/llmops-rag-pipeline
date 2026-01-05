module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = var.cluster_name
  cluster_version = "1.29"

  vpc_id     = var.vpc_id
  subnet_ids = var.private_subnet_ids

  # Security: Private endpoint + Public access (restricted usage)
  cluster_endpoint_public_access = true

  # OIDC for Service Accounts (Critical for Pods -> AWS Permissions)
  enable_irsa = true

  eks_managed_node_groups = {
    initial = {
      min_size     = 1
      max_size     = 2
      desired_size = 1

      instance_types = ["t3.medium"]
      capacity_type  = "ON_DEMAND"
    }
  }
}

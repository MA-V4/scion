terraform {
  required_version = ">= 1.9"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# TODO: EKS cluster, node groups (CPU for gateway, GPU for vLLM)
# TODO: RDS Postgres instance
# TODO: ElastiCache Redis cluster
# TODO: Application Load Balancer
# TODO: ECR repositories
# TODO: IAM roles and policies

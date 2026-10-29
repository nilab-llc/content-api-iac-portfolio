terraform {
  required_version = ">= 1.7, < 2.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

provider "aws" {
  profile             = var.aws_profile
  region              = "ap-northeast-1"
  allowed_account_ids = [var.aws_account_id]
  default_tags {
    tags = { Project = "content-api-iac", ManagedBy = "terraform" }
  }
}

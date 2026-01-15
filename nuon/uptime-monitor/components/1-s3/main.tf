terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.27.0"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      "install.nuon.co/id"     = var.install_id
      "component.nuon.co/name" = "s3"
    }
  }
}

variable "region" {
  type = string
}

variable "install_id" {
  type = string
}

locals {
  bucket_name = "${var.install_id}-uptime-monitor"
}

# S3 bucket
resource "aws_s3_bucket" "main" {
  bucket = local.bucket_name
}

# Outputs
output "bucket_name" {
  value       = aws_s3_bucket.main.bucket
  description = "S3 bucket name"
}

output "bucket_arn" {
  value       = aws_s3_bucket.main.arn
  description = "S3 bucket ARN"
}

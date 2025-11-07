terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.67.0"
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

# S3 bucket
resource "aws_s3_bucket" "main" {
  bucket = "${var.install_id}-uptime-monitor"
}

# IAM user for S3 access
resource "aws_iam_user" "s3_user" {
  name = "${var.install_id}-uptime-s3-user"

  tags = {
    Name = "${var.install_id}-uptime-s3-user"
  }
}

# IAM policy for S3 bucket access
resource "aws_iam_user_policy" "s3_policy" {
  name = "${var.install_id}-uptime-s3-policy"
  user = aws_iam_user.s3_user.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.main.arn,
          "${aws_s3_bucket.main.arn}/*"
        ]
      }
    ]
  })
}

# Create access key for the IAM user
resource "aws_iam_access_key" "s3_user" {
  user = aws_iam_user.s3_user.name
}

# Store secret access key in Secrets Manager
resource "aws_secretsmanager_secret" "access_key_secret" {
  name_prefix = "${var.install_id}-s3-access-key-secret-"
  description = "S3 access key secret for ${var.install_id}"

  tags = {
    Name = "${var.install_id}-s3-access-key-secret"
  }
}

resource "aws_secretsmanager_secret_version" "access_key_secret" {
  secret_id     = aws_secretsmanager_secret.access_key_secret.id
  secret_string = aws_iam_access_key.s3_user.secret
}

# Outputs
output "bucket_name" {
  value = aws_s3_bucket.main.bucket
}

output "access_key_id" {
  value       = aws_iam_access_key.s3_user.id
  description = "AWS access key ID for S3 bucket access"
}

output "access_key_secret_name" {
  value       = aws_secretsmanager_secret.access_key_secret.name
  description = "Name of the Secrets Manager secret containing S3 access key secret"
}

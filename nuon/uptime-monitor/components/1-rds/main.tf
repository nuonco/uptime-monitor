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
      "component.nuon.co/name" = "rds"
    }
  }
}

variable "region" {
  type = string
}

variable "install_id" {
  type = string
}

variable "vpc_id" {
  type        = string
  description = "VPC ID from the sandbox stack"
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs from the sandbox stack"
}

variable "node_security_group_id" {
  type        = string
  description = "EKS node security group ID from the sandbox stack"
}

# Security group for RDS
resource "aws_security_group" "postgres" {
  name_prefix = "${var.install_id}-postgres-"
  description = "Security group for PostgreSQL RDS instance"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.node_security_group_id]
    description     = "Allow PostgreSQL access from EKS nodes"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.install_id}-postgres-sg"
  }
}

# RDS subnet group
resource "aws_db_subnet_group" "postgres" {
  name_prefix = "${var.install_id}-postgres-"
  subnet_ids  = var.private_subnet_ids

  tags = {
    Name = "${var.install_id}-postgres-subnet-group"
  }
}

# Generate random password for PostgreSQL
resource "random_password" "postgres" {
  length  = 32
  special = true
}

# Store password in AWS Secrets Manager
resource "aws_secretsmanager_secret" "postgres_password" {
  name_prefix = "${var.install_id}-postgres-password-"
  description = "PostgreSQL database password for ${var.install_id}"

  tags = {
    Name = "${var.install_id}-postgres-password"
  }
}

resource "aws_secretsmanager_secret_version" "postgres_password" {
  secret_id     = aws_secretsmanager_secret.postgres_password.id
  secret_string = random_password.postgres.result
}

# RDS PostgreSQL instance
resource "aws_db_instance" "postgres" {
  identifier_prefix = "${var.install_id}-postgres-"

  engine         = "postgres"
  engine_version = "18"
  instance_class = "db.t3.micro"

  allocated_storage     = 10
  max_allocated_storage = 20
  storage_type          = "gp3"

  db_name  = "uptime_monitor"
  username = "uptime_monitor"
  password = random_password.postgres.result

  db_subnet_group_name   = aws_db_subnet_group.postgres.name
  vpc_security_group_ids = [aws_security_group.postgres.id]
  publicly_accessible    = false

  deletion_protection = true

  tags = {
    Name = "${var.install_id}-postgres"
  }
}

# Outputs
output "db_host" {
  value       = aws_db_instance.postgres.address
  description = "PostgreSQL database host"
}

output "db_port" {
  value       = aws_db_instance.postgres.port
  description = "PostgreSQL database port"
}

output "db_name" {
  value       = aws_db_instance.postgres.db_name
  description = "PostgreSQL database name"
}

output "db_username" {
  value       = aws_db_instance.postgres.username
  description = "PostgreSQL database username"
}

output "secret_name" {
  value       = aws_secretsmanager_secret.postgres_password.name
  description = "Name of the Secrets Manager secret containing the database password"
}

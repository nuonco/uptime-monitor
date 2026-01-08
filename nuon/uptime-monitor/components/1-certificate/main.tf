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
      "component.nuon.co/name" = "certificate"
    }
  }
}

variable "region" {
  type = string
}

variable "install_id" {
  type = string
}

variable "domain_name" {
  type = string
}

variable "zone_id" {
  type = string
}

module "certificate" {
  source  = "terraform-aws-modules/acm/aws"
  version = "~> 4.0"

  domain_name         = var.domain_name
  zone_id             = var.zone_id
  validation_method   = "DNS"
  wait_for_validation = false
}

output "public_domain_certificate_arn" {
  value = module.certificate.acm_certificate_arn
}

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Local state for this first pass -- simplest for a single operator.
  # An S3 backend + DynamoDB lock table is a well-known, easy upgrade later
  # if this ever needs multiple people applying changes.
}

provider "aws" {
  region = var.region
}

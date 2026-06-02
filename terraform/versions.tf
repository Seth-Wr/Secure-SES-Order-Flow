terraform {
  # Requires the latest stable Terraform CLI minor version (v1.15)
  # Allows automatic updates for patches (e.g., 1.15.5) but blocks 1.16.x
  required_version = "~> 1.15.0"

  required_providers {
    aws = {
      source = "hashicorp/aws"
      # Requires the stable AWS Provider v6.x
      # Allows bug fixes (e.g., 6.44.x) but blocks breaking changes in v7.0
      version = "~> 6.44.0"
    }
  }
}

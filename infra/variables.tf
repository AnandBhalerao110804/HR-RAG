variable "region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "ssh_allowed_cidr" {
  description = "CIDR block allowed to SSH into the instance -- your IP as x.x.x.x/32, not 0.0.0.0/0"
  type        = string
}

variable "anthropic_api_key" {
  description = "Anthropic API key -- stored in Secrets Manager, never committed. Supply via terraform.tfvars (gitignored) or TF_VAR_anthropic_api_key."
  type        = string
  sensitive   = true
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.small"
}

variable "repo_url" {
  description = "Public git URL to clone on boot"
  type        = string
  default     = "https://github.com/AnandBhalerao110804/HR-RAG.git"
}

variable "key_name" {
  description = "Name of an existing EC2 key pair, for SSH access"
  type        = string
}

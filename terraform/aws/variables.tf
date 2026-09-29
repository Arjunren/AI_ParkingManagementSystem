variable "aws_region" {
  description = "AWS region for the environment."
  type        = string
  default     = "ap-southeast-1"
}

variable "project_name" {
  description = "Short lowercase identifier used in resource names."
  type        = string
  default     = "parksmart-ai"
}

variable "environment" {
  description = "Deployment environment, such as staging or production."
  type        = string

  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be staging or production."
  }
}

variable "vpc_cidr" {
  description = "CIDR range for the dedicated VPC."
  type        = string
  default     = "10.42.0.0/16"
}

variable "container_image" {
  description = "Immutable ECR image URI (prefer a digest) for the ParkSmart web container."
  type        = string
}

variable "acm_certificate_arn" {
  description = "Issued ACM certificate ARN for the public HTTPS listener."
  type        = string
}

variable "allowed_ingress_cidrs" {
  description = "CIDRs permitted to reach the HTTPS load balancer."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "desired_count" {
  description = "Initial ECS web-task count."
  type        = number
  default     = 2
}

variable "database_instance_class" {
  description = "RDS PostgreSQL instance class."
  type        = string
  default     = "db.t4g.micro"
}

variable "database_name" {
  description = "Initial PostgreSQL database name."
  type        = string
  default     = "parksmart"
}

variable "database_url_secret_arn" {
  description = "Secrets Manager ARN containing the SQLAlchemy DATABASE_URL."
  type        = string
}

variable "flask_secret_key_secret_arn" {
  description = "Secrets Manager ARN containing the Flask SECRET_KEY."
  type        = string
}

variable "openai_api_key_secret_arn" {
  description = "Secrets Manager ARN containing OPENAI_API_KEY."
  type        = string
}

variable "ratelimit_storage_uri_secret_arn" {
  description = "Optional Secrets Manager ARN containing RATELIMIT_STORAGE_URI, typically a private Redis URL."
  type        = string
  default     = null
  nullable    = true
}

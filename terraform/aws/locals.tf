data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  azs         = slice(data.aws_availability_zones.available.names, 0, 2)

  common_tags = {
    Application = "ParkSmart AI"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

output "load_balancer_dns_name" {
  description = "Public DNS name for the HTTPS application load balancer."
  value       = aws_lb.web.dns_name
}

output "database_endpoint" {
  description = "Private PostgreSQL endpoint. Do not expose it publicly."
  value       = aws_db_instance.main.address
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group used by the web tasks."
  value       = aws_cloudwatch_log_group.app.name
}

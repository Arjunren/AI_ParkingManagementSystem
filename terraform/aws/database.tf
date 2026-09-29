resource "aws_db_subnet_group" "main" {
  name       = "${local.name_prefix}-database"
  subnet_ids = [for subnet in aws_subnet.database : subnet.id]
}

resource "aws_db_instance" "main" {
  identifier                 = local.name_prefix
  engine                     = "postgres"
  engine_version             = "16"
  instance_class             = var.database_instance_class
  allocated_storage          = 20
  max_allocated_storage      = 100
  storage_encrypted          = true
  db_name                    = var.database_name
  username                   = "parksmart_admin"
  manage_master_user_password = true
  publicly_accessible        = false
  multi_az                   = var.environment == "production"
  db_subnet_group_name       = aws_db_subnet_group.main.name
  vpc_security_group_ids     = [aws_security_group.database.id]
  backup_retention_period    = var.environment == "production" ? 14 : 7
  deletion_protection        = var.environment == "production"
  skip_final_snapshot        = var.environment != "production"
  final_snapshot_identifier  = var.environment == "production" ? "${local.name_prefix}-final" : null
  copy_tags_to_snapshot      = true
  auto_minor_version_upgrade = true
  apply_immediately          = false
}

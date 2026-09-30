resource "aws_db_subnet_group" "main" {
  name       = "faultlab-${var.environment}"
  subnet_ids = aws_subnet.private[*].id
}
resource "aws_db_instance" "main" {
  identifier                  = "faultlab-${var.environment}"
  engine                      = "postgres"
  engine_version              = "16"
  instance_class              = var.db_instance_class
  allocated_storage           = 20
  storage_type                = "gp3"
  storage_encrypted           = true
  db_name                     = "faultlab"
  username                    = "faultlab"
  manage_master_user_password = true
  db_subnet_group_name        = aws_db_subnet_group.main.name
  vpc_security_group_ids      = [aws_security_group.database.id]
  publicly_accessible         = false
  backup_retention_period     = 1
  deletion_protection         = false
  skip_final_snapshot         = true
  apply_immediately           = true
}

resource "aws_elasticache_subnet_group" "main" {
  name       = "faultlab-${var.environment}"
  subnet_ids = aws_subnet.private[*].id
}
resource "aws_elasticache_replication_group" "main" {
  replication_group_id       = "faultlab-${var.environment}"
  description                = "FaultLab demo Redis"
  engine                     = "redis"
  node_type                  = var.redis_node_type
  num_cache_clusters         = 1
  automatic_failover_enabled = false
  subnet_group_name          = aws_elasticache_subnet_group.main.name
  security_group_ids         = [aws_security_group.redis.id]
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  snapshot_retention_limit   = 1
}

resource "aws_ecr_repository" "app" {
  name = "faultlab-${var.environment}-app"
  image_scanning_configuration { scan_on_push = true }
  encryption_configuration { encryption_type = "AES256" }
}
resource "aws_ecr_repository" "frontend" {
  name = "faultlab-${var.environment}-frontend"
  image_scanning_configuration { scan_on_push = true }
  encryption_configuration { encryption_type = "AES256" }
}

data "aws_caller_identity" "current" {}

locals {
  app_image      = "${aws_ecr_repository.app.repository_url}:${var.image_tag}"
  frontend_image = "${aws_ecr_repository.frontend.repository_url}:${var.image_tag}"
  services = {
    frontend = { port = 80, cpu = 256, memory = 512, command = [], image = local.frontend_image }
    backend  = { port = 8000, cpu = 256, memory = 512, command = ["sh", "-c", "alembic upgrade head && uvicorn faultlab.api:app --host 0.0.0.0 --port 8000"], image = local.app_image }
    worker   = { port = 0, cpu = 256, memory = 512, command = ["python", "-m", "faultlab.worker"], image = local.app_image }
    gateway  = { port = 8001, cpu = 256, memory = 512, command = ["uvicorn", "demo.gateway:app", "--host", "0.0.0.0", "--port", "8001"], image = local.app_image }
    order    = { port = 8002, cpu = 256, memory = 512, command = ["uvicorn", "demo.order:app", "--host", "0.0.0.0", "--port", "8002"], image = local.app_image }
    payment  = { port = 8003, cpu = 256, memory = 512, command = ["uvicorn", "demo.payment:app", "--host", "0.0.0.0", "--port", "8003"], image = local.app_image }
  }
  database_environment = [
    { name = "DB_HOST", value = aws_db_instance.main.address },
    { name = "DB_NAME", value = "faultlab" },
    { name = "DB_USER", value = "faultlab" },
    { name = "REDIS_URL", value = "rediss://${aws_elasticache_replication_group.main.primary_endpoint_address}:6379/0" },
    { name = "DEMO_GATEWAY_URL", value = "http://gateway.faultlab.local:8001" },
    { name = "DEMO_PAYMENT_URL", value = "http://payment.faultlab.local:8003" }
  ]
}

resource "aws_iam_role" "execution" {
  name               = "faultlab-${var.environment}-execution"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" }, Action = "sts:AssumeRole" }] })
}
resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}
resource "aws_iam_role_policy" "secrets" {
  name = "faultlab-${var.environment}-secrets"
  role = aws_iam_role.execution.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect   = "Allow", Action = ["secretsmanager:GetSecretValue"],
    Resource = [aws_db_instance.main.master_user_secret[0].secret_arn, var.internal_token_secret_arn]
  }] })
}
resource "aws_iam_role" "task" {
  name               = "faultlab-${var.environment}-task"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" }, Action = "sts:AssumeRole" }] })
}

resource "aws_cloudwatch_log_group" "service" {
  for_each          = local.services
  name              = "/ecs/faultlab/${var.environment}/${each.key}"
  retention_in_days = 7
}
resource "aws_ecs_cluster" "main" { name = "faultlab-${var.environment}" }

resource "aws_service_discovery_private_dns_namespace" "demo" {
  name = "faultlab.local"
  vpc  = aws_vpc.main.id
}
resource "aws_service_discovery_service" "demo" {
  for_each = { for name in ["gateway", "order", "payment"] : name => name }
  name     = each.key
  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.demo.id
    dns_records {
      ttl  = 10
      type = "A"
    }
  }
  health_check_custom_config { failure_threshold = 1 }
}

resource "aws_ecs_task_definition" "service" {
  for_each                 = local.services
  family                   = "faultlab-${var.environment}-${each.key}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = each.value.cpu
  memory                   = each.value.memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  container_definitions = jsonencode([{
    name         = each.key
    image        = each.value.image
    essential    = true
    command      = length(each.value.command) > 0 ? each.value.command : null
    portMappings = each.value.port == 0 ? [] : [{ containerPort = each.value.port, hostPort = each.value.port, protocol = "tcp" }]
    environment = concat(
      contains(["backend", "worker"], each.key) ? local.database_environment : [],
      each.key == "gateway" ? [{ name = "ORDER_URL", value = "http://order.faultlab.local:8002" }] : [],
      each.key == "order" ? [{ name = "PAYMENT_URL", value = "http://payment.faultlab.local:8003" }] : []
    )
    secrets = concat(
      contains(["backend", "worker"], each.key) ? [{ name = "DB_PASSWORD", valueFrom = "${aws_db_instance.main.master_user_secret[0].secret_arn}:password::" }] : [],
      contains(["backend", "worker", "payment"], each.key) ? [{ name = "INTERNAL_TOKEN", valueFrom = var.internal_token_secret_arn }] : []
    )
    logConfiguration = { logDriver = "awslogs", options = {
      "awslogs-group"         = aws_cloudwatch_log_group.service[each.key].name,
      "awslogs-region"        = var.aws_region,
      "awslogs-stream-prefix" = "app"
    } }
  }])
}

resource "aws_lb" "main" {
  name               = "faultlab-${var.environment}"
  load_balancer_type = "application"
  subnets            = aws_subnet.public[*].id
  security_groups    = [aws_security_group.alb.id]
  idle_timeout       = 300
}
resource "aws_lb_target_group" "frontend" {
  name        = "faultlab-${var.environment}-ui"
  port        = 80
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = aws_vpc.main.id
  health_check {
    path    = "/"
    matcher = "200"
  }
}
resource "aws_lb_target_group" "backend" {
  name        = "faultlab-${var.environment}-api"
  port        = 8000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = aws_vpc.main.id
  health_check {
    path    = "/ready"
    matcher = "200"
  }
}
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}
resource "aws_lb_listener_rule" "backend" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 10
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }
  condition {
    path_pattern { values = ["/api/*", "/ws/*", "/health", "/ready"] }
  }
}

resource "aws_ecs_service" "service" {
  for_each                           = local.services
  name                               = "faultlab-${var.environment}-${each.key}"
  cluster                            = aws_ecs_cluster.main.id
  task_definition                    = aws_ecs_task_definition.service[each.key].arn
  desired_count                      = var.start_services ? 1 : 0
  launch_type                        = "FARGATE"
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100
  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.tasks.id]
    assign_public_ip = false
  }
  dynamic "load_balancer" {
    for_each = contains(["frontend", "backend"], each.key) ? [1] : []
    content {
      target_group_arn = each.key == "frontend" ? aws_lb_target_group.frontend.arn : aws_lb_target_group.backend.arn
      container_name   = each.key
      container_port   = each.value.port
    }
  }
  dynamic "service_registries" {
    for_each = contains(["gateway", "order", "payment"], each.key) ? [1] : []
    content { registry_arn = aws_service_discovery_service.demo[each.key].arn }
  }
  depends_on = [aws_lb_listener.https, aws_iam_role_policy_attachment.execution, aws_iam_role_policy.secrets]
}

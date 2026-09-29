resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${local.name_prefix}"
  retention_in_days = 30
}

resource "aws_ecs_cluster" "main" {
  name = local.name_prefix

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

data "aws_iam_policy_document" "task_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "task_execution" {
  name               = "${local.name_prefix}-task-execution"
  assume_role_policy = data.aws_iam_policy_document.task_assume_role.json
}

resource "aws_iam_role_policy_attachment" "task_execution" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "task_execution_secrets" {
  statement {
    actions = ["secretsmanager:GetSecretValue"]
    resources = compact([
      var.database_url_secret_arn,
      var.flask_secret_key_secret_arn,
      var.openai_api_key_secret_arn,
      var.ratelimit_storage_uri_secret_arn,
    ])
  }
}

resource "aws_iam_role_policy" "task_execution_secrets" {
  name   = "${local.name_prefix}-read-runtime-secrets"
  role   = aws_iam_role.task_execution.id
  policy = data.aws_iam_policy_document.task_execution_secrets.json
}

resource "aws_iam_role" "task" {
  name               = "${local.name_prefix}-task"
  assume_role_policy = data.aws_iam_policy_document.task_assume_role.json
}

locals {
  runtime_secrets = concat(
    [
      { name = "DATABASE_URL", valueFrom = var.database_url_secret_arn },
      { name = "SECRET_KEY", valueFrom = var.flask_secret_key_secret_arn },
      { name = "OPENAI_API_KEY", valueFrom = var.openai_api_key_secret_arn },
    ],
    var.ratelimit_storage_uri_secret_arn == null ? [] : [
      { name = "RATELIMIT_STORAGE_URI", valueFrom = var.ratelimit_storage_uri_secret_arn },
    ],
  )
}

resource "aws_ecs_task_definition" "web" {
  family                   = "${local.name_prefix}-web"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = "web"
    image     = var.container_image
    essential = true
    portMappings = [{
      containerPort = 8000
      protocol      = "tcp"
    }]
    environment = [
      { name = "FLASK_ENV", value = "production" },
      { name = "OPENAI_MODEL", value = "gpt-5-mini" },
    ]
    secrets = local.runtime_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.app.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "web"
      }
    }
  }])
}

resource "aws_ecs_service" "web" {
  name                               = "web"
  cluster                            = aws_ecs_cluster.main.id
  task_definition                    = aws_ecs_task_definition.web.arn
  desired_count                      = var.desired_count
  launch_type                        = "FARGATE"
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200

  network_configuration {
    assign_public_ip = false
    security_groups  = [aws_security_group.app.id]
    subnets          = [for subnet in aws_subnet.app : subnet.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.web.arn
    container_name   = "web"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.https]
}

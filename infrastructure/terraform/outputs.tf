output "https_endpoint" { value = "https://${var.domain_name}" }
output "alb_dns_name" { value = aws_lb.main.dns_name }
output "app_repository" { value = aws_ecr_repository.app.repository_url }
output "frontend_repository" { value = aws_ecr_repository.frontend.repository_url }
output "cluster_name" { value = aws_ecs_cluster.main.name }

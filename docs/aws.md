# AWS deployment plan

Intended topology: HTTPS ALB to frontend/backend ECS Fargate tasks in private subnets; worker and demo services as private ECS services; ECR repositories for immutable images; private RDS PostgreSQL and ElastiCache Redis; CloudWatch logs; Secrets Manager for database and internal fault token; dedicated VPC security groups with database/cache ingress only from the relevant task groups.

For an economical demo, use one NAT gateway only if image pulls and outbound calls require it, small task sizes, and short-lived resources. A single NAT gateway reduces cost but removes AZ redundancy. Avoid public database/cache endpoints. Terraform remote state should use an encrypted S3 bucket and locking. IAM policies should be scoped to specific repositories, log groups, and secret ARNs.

**Status:** The AWS stack is not yet implemented or deployed. There are no valid `terraform init/plan/apply/destroy` commands for this repository yet. Cloud failure and rollback tests have not run. The application also needs API authentication, a robust active-service lock, and reliable worker ownership before internet exposure or worker scaling.

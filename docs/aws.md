# AWS deployment

The Terraform stack in `infrastructure/terraform/` provisions a dedicated VPC with two public and two private subnets, one NAT gateway, an HTTPS ALB, six ECS/Fargate services, private RDS PostgreSQL, private encrypted Redis, two ECR repositories, CloudWatch log groups, scoped security groups, Cloud Map DNS for the demo chain, and ECS roles. RDS manages its own master password in Secrets Manager. The fault token is supplied as an existing Secrets Manager secret. The ALB only accepts the trusted CIDRs supplied by the operator.

Terraform formatting and provider-aware validation passed locally with Terraform 1.16.4 and AWS provider 5.100.0. **No AWS plan or apply has run**, because an account, certificate, DNS name, state bucket, and credentials were not supplied. Treat the first deployment as a reviewable trial, not a verified production release.

## Prerequisites

1. A dedicated AWS account or tightly scoped demo environment and AWS CLI credentials with permissions to create the listed resources.
2. An S3 bucket for encrypted, versioned Terraform state. Restrict access and enable state locking with `use_lockfile=true`. Keep it outside this stack so destroy cannot delete its own state.
3. An ACM certificate in the chosen region for a domain you control.
4. A Secrets Manager secret containing a long random internal token as a **plain string**. Supply its ARN as `internal_token_secret_arn`.
5. Docker, Terraform ≥1.7, and AWS CLI. Review estimated NAT, RDS, Redis, ALB, and six Fargate task costs before starting services.

Create an ignored `infrastructure/terraform/terraform.tfvars`:

```hcl
aws_region                = "us-east-1"
environment               = "demo"
domain_name               = "faultlab.example.com"
certificate_arn           = "arn:aws:acm:us-east-1:ACCOUNT:certificate/ID"
internal_token_secret_arn = "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:NAME"
allowed_cidrs             = ["YOUR_PUBLIC_IP/32"]
image_tag                 = "YOUR_GIT_SHA"
start_services            = false
```

The `terraform.tfvars` file is ignored by Git. Terraform state may contain sensitive infrastructure metadata; never commit it.

## Provision and deploy

Run from `infrastructure/terraform/` (replace the state bucket and region):

```bash
terraform init -backend-config="bucket=YOUR_VERSIONED_STATE_BUCKET" -backend-config="key=faultlab/demo.tfstate" -backend-config="region=us-east-1" -backend-config="encrypt=true" -backend-config="use_lockfile=true"
terraform fmt -check -recursive
terraform validate
terraform plan -out=faultlab.tfplan
terraform apply faultlab.tfplan
```

The first apply creates infrastructure with service desired counts at zero. From the repository root, build and push immutable image tags using the repository outputs:

```bash
APP_REPO=$(terraform -chdir=infrastructure/terraform output -raw app_repository)
UI_REPO=$(terraform -chdir=infrastructure/terraform output -raw frontend_repository)
TAG=$(git rev-parse --short=12 HEAD)
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin "$(echo "$APP_REPO" | cut -d/ -f1)"
docker build -t "$APP_REPO:$TAG" .
docker build -t "$UI_REPO:$TAG" frontend
docker push "$APP_REPO:$TAG"
docker push "$UI_REPO:$TAG"
```

Set `image_tag` to the pushed tag in `terraform.tfvars`, point your domain at `alb_dns_name`, then run:

```bash
terraform -chdir=infrastructure/terraform plan -var='start_services=true' -out=faultlab-start.tfplan
terraform -chdir=infrastructure/terraform apply faultlab-start.tfplan
```

The backend task runs the Alembic migration before serving. The worker retries while dependencies start. Check ECS service health, ALB target health, and CloudWatch logs before registering the demo gateway through the UI.

For teardown, set `start_services=false` and apply, then run `terraform -chdir=infrastructure/terraform destroy`. Destroy removes the database and its data because this is a disposable demo; preserve data separately if needed.

## Failure and rollback drills

In the dedicated environment only, replace one ECS task at a time and observe health recovery and persistent experiment history. Revert `image_tag` to a known-good ECR tag and apply for rollback. Test RDS/Redis connection interruptions, backend and worker replacement, WebSocket reconnection, and scaling only after adding API authentication and a service-scoped experiment lock. These cloud drills have **not run**.

## Limits before broad exposure

The API lacks user authentication. Keep `allowed_cidrs` narrow. The single worker's lease recovery is best-effort, and cleanup failure remains operator-visible. RDS password rotation requires task refresh. Multiworker and multi-API scale need atomic ownership and conflict enforcement. NAT is single-AZ for cost and is a single point of failure. There is no automated deployment or rollback workflow; CI builds images but does not push or deploy them.

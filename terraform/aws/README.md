# ParkSmart AI AWS Terraform foundation

This reference configuration deploys a high-availability web tier: two public subnets hosting an HTTPS Application Load Balancer, two private application subnets hosting ECS Fargate tasks, two isolated database subnets, private RDS PostgreSQL, CloudWatch logs, and narrowly scoped security groups.

It intentionally does **not** create secrets or put their values into Terraform. Instead, pass existing AWS Secrets Manager ARNs for `DATABASE_URL`, `SECRET_KEY`, `OPENAI_API_KEY`, and optionally `RATELIMIT_STORAGE_URI`. ECS injects those values at task start; its execution role is scoped to those ARNs.

## Prerequisites

- Terraform 1.7+ and AWS CLI credentials for the target account.
- An issued ACM certificate in the same region as the load balancer.
- An immutable image in ECR (prefer an image digest).
- Secrets Manager entries with plain secret-string values:
  - `DATABASE_URL`: TLS-enabled SQLAlchemy PostgreSQL URL.
  - `SECRET_KEY`: high-entropy Flask session key.
  - `OPENAI_API_KEY`: server-side OpenAI credential.
  - `RATELIMIT_STORAGE_URI` (optional initially): private Redis URL for shared rate limiting.

## Plan safely

```bash
cd terraform/aws
cp terraform.tfvars.example staging.tfvars
# Edit only account-specific IDs, ARNs, and the immutable image URI.
terraform init -backend-config=backend.hcl
terraform fmt -check -recursive
terraform validate
terraform plan -var-file=staging.tfvars
```

Use a CI identity and environment approval for production applies. Before pointing traffic to a deployment, run `flask db upgrade` as a one-off ECS task on the same private network and with the same database secret. Do not start multiple web tasks with the in-process AI Factory thread for a long-running production workload; introduce the durable worker and queue described in the project blueprint first.

## Security boundaries

- The ALB accepts HTTPS only. ECS tasks are private and accept port 8000 only from the ALB.
- RDS is private and accepts PostgreSQL only from ECS tasks. It is encrypted, backed up, and deletion-protected in production.
- The ECS execution role can read only the supplied secret ARNs; no secret value appears in outputs or the example variables.
- The app security group currently permits outbound HTTPS/provider traffic and database access. For a mature deployment, add VPC endpoints and egress controls for exactly the required services.

The design deliberately leaves DNS/WAF, Redis/queue, alerting, image build/push, and a durable factory worker as separate follow-up modules: each needs organization-specific domains, retention, budget, and operational ownership decisions.

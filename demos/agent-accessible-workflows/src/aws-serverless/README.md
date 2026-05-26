# AWS serverless DESeq demo (optional)

> **Not used by production portfolio pages.** The public site uses static sample outputs from `demos/agent-accessible-workflows/outputs/`. Deploy this stack only on a **preview branch** for personal QA. Do not set `deseq_api_url` on `main`. See the main demo README for the preview-only policy.

Deploys a Free-Tier-friendly HTTP API on AWS Lambda (container worker + zip API handler) with DynamoDB job state and S3 artifacts. Same routes as local FastAPI: `GET /healthz`, `POST /tools/run_deseq`, `GET /jobs/{id}`.

## HTTPS

The default `api_base_url` from `terraform apply` is already **HTTPS** (`https://….execute-api.<region>.amazonaws.com`). AWS terminates TLS with a managed certificate; no extra setup is required for agents, curl, or the portfolio page.

For a branded hostname (e.g. `api.yourdomain.com`):

1. Set `api_custom_domain` in `terraform.tfvars`.
2. **Route 53:** also set `route53_zone_id` — Terraform requests an ACM certificate, validates it, and creates alias records.
3. **Cloudflare / other DNS:** run `terraform apply` once, add the `acm_dns_validation` CNAME records from Terraform output, wait until the cert is `ISSUED`, set `acm_certificate_arn` in tfvars, apply again, then CNAME `api_custom_domain` to `api_custom_domain_target.hostname` (DNS only; orange-cloud proxy optional).

On a **preview branch only**, you may set Jekyll `deseq_api_url` in `_config.yml` to the HTTPS API URL (custom or execute-api) to test live integration. Keep `deseq_api_url` empty on `main`. The portfolio site is served over HTTPS; any live API URL must use `https://` to avoid mixed-content blocking.

## Prerequisites

- AWS CLI configured (`aws sts get-caller-identity`)
- Terraform >= 1.5
- Docker (worker container image)
- Python 3.12+ (local parity tests)

## Deploy

From `demos/agent-accessible-workflows`:

```bash
# 1. Create ECR repo (once), then build and push (replace account/region/repo)
aws ecr create-repository --repository-name deseq-worker --region us-east-1  # skip if exists
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
# Windows/Docker Desktop: Lambda needs linux/amd64 + Docker v2 manifest (not OCI index)
docker build --platform linux/amd64 --provenance=false --sbom=false \
  -f src/aws-serverless/lambda/worker/Dockerfile \
  -t <account-id>.dkr.ecr.us-east-1.amazonaws.com/deseq-worker:latest .
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/deseq-worker:latest

# 2. Configure Terraform
cp src/aws-serverless/terraform.tfvars.example src/aws-serverless/terraform/terraform.tfvars
# Edit api_token and worker_image_uri

# 3. Apply
cd src/aws-serverless/terraform
terraform init
terraform validate
terraform plan
terraform apply
```

Note the `api_base_url` output. Set Cloudflare Worker `API_BASE_URL` in `src/gateway/wrangler.jsonc` (or Wrangler secrets) to that URL, and `API_JWT` to the same bearer token as `api_token`.

## Destroy (return to ~$0)

```bash
cd src/aws-serverless/terraform
terraform destroy
```

Empty the ECR repository if you created one. DynamoDB and S3 objects expire automatically via TTL/lifecycle (7 days by default).

## Smoke test (manual)

Replace `API_URL` and `TOKEN` after `terraform apply`:

```bash
export API_URL="https://xxxx.execute-api.us-east-1.amazonaws.com"
export TOKEN="your-api-token"

curl -sS "$API_URL/healthz"

JOB=$(curl -sS -X POST "$API_URL/tools/run_deseq" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dataset":"synthetic","synthetic_profile":"serverless"}')
echo "$JOB"
JOB_ID=$(echo "$JOB" | python -c "import sys,json; print(json.load(sys.stdin)['job_id'])")

for i in $(seq 1 40); do
  STATUS=$(curl -sS -H "Authorization: Bearer $TOKEN" "$API_URL/jobs/$JOB_ID")
  echo "$STATUS" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('status'))"
  echo "$STATUS" | grep -q '"status": "completed"' && break
  sleep 3
done

curl -sS -H "Authorization: Bearer $TOKEN" "$API_URL/jobs/$JOB_ID" | python -m json.tool
```

Expected: `queued` → `running` → `completed` with presigned URLs in `artifacts` for `results.csv`, `top_genes.csv`, `volcano.png`.

**Stuck in `queued`?** Check CloudWatch log group `/aws/lambda/deseq-demo-worker`. Common causes: DynamoDB reserved word `status` (fixed in worker handler), or Lambda’s `JOBLIB_MULTIPROCESSING=0` breaking PyDESeq2 (worker unsets this before import). Rebuild/push the worker image and run `terraform apply` or `aws lambda update-function-code` after code changes.

## Cost guardrails

- `worker_reserved_concurrency = -1` (default; new accounts have a 10 concurrent limit—do not reserve until quota is raised)
- `worker_memory_mb = 2048`, `worker_timeout_seconds = 120`
- No NAT Gateway, ALB, Redis, or EC2
- S3 lifecycle + DynamoDB TTL (7 days)
- Set an AWS Budget alert at **$1** in the console (optional; not created by Terraform)

## Local parity

```bash
pip install -r requirements.txt
python scripts/regenerate-portfolio-outputs.py
```

Uses the `serverless` synthetic profile (100 genes × 8 samples).

# Oracle Cloud deployment walkthrough

This folder provisions a small Oracle Cloud Infrastructure VM for the DESeq
workflow backend. It is designed for the Always Free ARM shape and runs the
same Docker Compose stack used locally.

## What this deploys

- One `VM.Standard.A1.Flex` instance.
- Ubuntu 22.04 image from the current Oracle Linux/Ubuntu image list.
- A public IP for initial testing.
- Ingress rules for:
  - SSH (`22`)
  - FastAPI (`8000`)
  - MinIO console/API (`9000`, `9001`) for demo parity
- `cloud-init.yaml`, which installs Docker, clones this repository, and starts:
  - `api`
  - `redis`
  - `worker`
  - `minio`

For a public deployment, place Cloudflare in front of the API and restrict
direct ingress to Cloudflare source IPs or a private network.

## Prerequisites

Install:

- Terraform
- OCI CLI credentials, or equivalent environment variables for the OCI provider
- An SSH public key

Set variables in a `terraform.tfvars` file:

```hcl
tenancy_ocid     = "ocid1.tenancy.oc1..."
compartment_ocid = "ocid1.compartment.oc1..."
region           = "us-ashburn-1"
ssh_public_key   = "ssh-ed25519 AAAA..."
repo_url         = "https://github.com/BKAmos/BKAmos.github.io.git"
repo_ref         = "main"
api_token        = "replace-with-a-long-random-token"
```

## Deploy

```bash
terraform init
terraform plan
terraform apply
```

After apply completes, Terraform prints:

- `public_ip`
- `api_base_url`
- `minio_console_url`

## Smoke test

```bash
export API_BASE_URL="http://<public_ip>:8000"
export TOKEN="replace-with-a-long-random-token"

curl "$API_BASE_URL/healthz"

curl -X POST "$API_BASE_URL/tools/run_deseq" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "synthetic",
    "condition_column": "condition",
    "reference_level": "control",
    "treatment_level": "treated",
    "batch_column": "batch",
    "min_count": 10
  }'
```

Poll:

```bash
curl -H "Authorization: Bearer $TOKEN" "$API_BASE_URL/jobs/<job_id>"
```

## Connect Cloudflare Worker

After the API is reachable:

```bash
cd ../gateway
npx wrangler secret put API_JWT
npx wrangler deploy
```

Set `API_BASE_URL` in `wrangler.jsonc` or through Worker environment variables
to the API base URL. The portfolio UI should point to:

```text
https://<worker-subdomain>.workers.dev/api
```

## Operational notes

- The included MinIO service is intended for demo parity. For production,
  replace it with Oracle Object Storage and signed upload/download URLs.
- Do not accept sensitive human data until authentication, retention, deletion,
  audit logging, and compliance controls are reviewed.
- The A1 shape is suitable for toy datasets and small examples, not large
  production RNA-seq cohorts.

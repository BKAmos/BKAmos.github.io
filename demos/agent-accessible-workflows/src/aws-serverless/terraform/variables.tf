variable "aws_region" {
  description = "AWS region (us-east-1 recommended for Free Tier)."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Prefix for resource names."
  type        = string
  default     = "deseq-demo"
}

variable "api_token" {
  description = "Bearer token for POST/GET job endpoints (set via tfvars, not committed)."
  type        = string
  sensitive   = true
}

variable "worker_image_uri" {
  description = "ECR image URI for the worker Lambda container (build and push before apply)."
  type        = string
  default     = "public.ecr.aws/lambda/python:3.12"
}

variable "worker_memory_mb" {
  description = "Worker Lambda memory (MB). Tune after first invoke."
  type        = number
  default     = 2048
}

variable "worker_timeout_seconds" {
  description = "Worker Lambda timeout."
  type        = number
  default     = 120
}

variable "worker_reserved_concurrency" {
  description = "Reserved worker concurrency. Use -1 (default) on new accounts (10 concurrent limit); set 2+ only after raising the account quota."
  type        = number
  default     = -1
}

variable "cors_allow_origin" {
  description = "CORS Allow-Origin for API responses."
  type        = string
  default     = "*"
}

variable "artifact_url_ttl_seconds" {
  description = "Presigned S3 URL lifetime."
  type        = number
  default     = 3600
}

variable "job_ttl_days" {
  description = "DynamoDB TTL and S3 lifecycle (days)."
  type        = number
  default     = 7
}

variable "api_custom_domain" {
  description = "Optional custom hostname (e.g. api.example.com). Leave empty to use the default execute-api HTTPS URL."
  type        = string
  default     = ""
}

variable "route53_zone_id" {
  description = "Route 53 hosted zone ID for api_custom_domain. When set, Terraform requests and validates an ACM certificate and creates DNS alias records."
  type        = string
  default     = ""
}

variable "acm_certificate_arn" {
  description = "Optional existing validated ACM certificate ARN in the same region as the API. Use when DNS is outside Route 53 (e.g. Cloudflare) after manual ACM validation."
  type        = string
  default     = ""
}

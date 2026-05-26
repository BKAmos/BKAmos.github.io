resource "aws_lambda_function" "worker" {
  function_name = "${local.name_prefix}-worker"
  role          = aws_iam_role.worker_lambda.arn
  package_type  = "Image"
  image_uri     = var.worker_image_uri
  timeout       = var.worker_timeout_seconds
  memory_size   = var.worker_memory_mb

  reserved_concurrent_executions = var.worker_reserved_concurrency

  environment {
    variables = {
      JOBS_TABLE_NAME       = aws_dynamodb_table.jobs.name
      ARTIFACTS_BUCKET_NAME = aws_s3_bucket.artifacts.bucket
      JOB_TTL_DAYS          = tostring(var.job_ttl_days)
    }
  }

  tags = {
    Project = local.name_prefix
  }
}

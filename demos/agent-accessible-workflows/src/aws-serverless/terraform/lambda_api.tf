data "archive_file" "api_lambda" {
  type        = "zip"
  output_path = "${path.module}/.build/api_lambda.zip"

  source {
    content  = file("${path.module}/../lambda/api/handler.py")
    filename = "handler.py"
  }

  source {
    content  = file("${path.module}/../lambda/shared/config.py")
    filename = "shared/config.py"
  }

  source {
    content  = file("${path.module}/../lambda/shared/__init__.py")
    filename = "shared/__init__.py"
  }
}

resource "aws_lambda_function" "api" {
  function_name = "${local.name_prefix}-api"
  role          = aws_iam_role.api_lambda.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 256

  filename         = data.archive_file.api_lambda.output_path
  source_code_hash = data.archive_file.api_lambda.output_base64sha256

  environment {
    variables = {
      JOBS_TABLE_NAME         = aws_dynamodb_table.jobs.name
      ARTIFACTS_BUCKET_NAME   = aws_s3_bucket.artifacts.bucket
      WORKER_FUNCTION_NAME    = aws_lambda_function.worker.function_name
      API_TOKEN               = var.api_token
      ARTIFACT_URL_TTL_SECONDS = tostring(var.artifact_url_ttl_seconds)
      JOB_TTL_DAYS            = tostring(var.job_ttl_days)
      CORS_ALLOW_ORIGIN       = var.cors_allow_origin
    }
  }

  tags = {
    Project = local.name_prefix
  }
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}

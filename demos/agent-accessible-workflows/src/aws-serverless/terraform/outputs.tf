output "api_base_url" {
  description = "HTTPS API base URL (no trailing slash). Custom domain when configured, otherwise the execute-api URL. Set Cloudflare Worker API_BASE_URL to this value."
  value = local.enable_custom_domain && length(aws_apigatewayv2_domain_name.api) > 0 ? "https://${var.api_custom_domain}" : aws_apigatewayv2_api.http.api_endpoint
}

output "api_execute_url" {
  description = "Default API Gateway HTTPS URL (always available)."
  value       = aws_apigatewayv2_api.http.api_endpoint
}

output "acm_dns_validation" {
  description = "ACM DNS validation records when api_custom_domain is set without route53_zone_id. Add these in your DNS provider, wait for ISSUED, set acm_certificate_arn, then apply again."
  value = local.enable_custom_domain && var.route53_zone_id == "" && var.acm_certificate_arn == "" && length(aws_acm_certificate.api) > 0 ? [
    for dvo in aws_acm_certificate.api[0].domain_validation_options : {
      name  = dvo.resource_record_name
      type  = dvo.resource_record_type
      value = dvo.resource_record_value
    }
  ] : []
}

output "api_custom_domain_target" {
  description = "API Gateway regional target for a manual CNAME (Cloudflare etc.) when using a custom domain."
  value = length(aws_apigatewayv2_domain_name.api) > 0 ? {
    hostname = aws_apigatewayv2_domain_name.api[0].domain_name_configuration[0].target_domain_name
    zone_id  = aws_apigatewayv2_domain_name.api[0].domain_name_configuration[0].hosted_zone_id
  } : null
}

output "artifact_bucket" {
  description = "S3 bucket for run artifacts."
  value       = aws_s3_bucket.artifacts.bucket
}

output "jobs_table" {
  description = "DynamoDB jobs table name."
  value       = aws_dynamodb_table.jobs.name
}

output "worker_function_name" {
  description = "Worker Lambda function name."
  value       = aws_lambda_function.worker.function_name
}

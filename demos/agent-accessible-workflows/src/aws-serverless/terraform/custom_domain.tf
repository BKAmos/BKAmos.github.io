locals {
  enable_custom_domain = var.api_custom_domain != ""
  use_route53_acm      = local.enable_custom_domain && var.route53_zone_id != ""
  custom_cert_arn = local.enable_custom_domain ? coalesce(
    var.acm_certificate_arn != "" ? var.acm_certificate_arn : null,
    local.use_route53_acm ? aws_acm_certificate_validation.api[0].certificate_arn : null,
    try(aws_acm_certificate.api[0].arn, null),
  ) : null
}

resource "aws_acm_certificate" "api" {
  count = local.enable_custom_domain && var.acm_certificate_arn == "" ? 1 : 0

  domain_name       = var.api_custom_domain
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "acm_validation" {
  for_each = local.use_route53_acm ? {
    for dvo in aws_acm_certificate.api[0].domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}

  zone_id = var.route53_zone_id
  name    = each.value.name
  type    = each.value.type
  ttl     = 60
  records = [each.value.record]
}

resource "aws_acm_certificate_validation" "api" {
  count = local.use_route53_acm ? 1 : 0

  certificate_arn         = aws_acm_certificate.api[0].arn
  validation_record_fqdns = [for record in aws_route53_record.acm_validation : record.fqdn]
}

resource "aws_apigatewayv2_domain_name" "api" {
  count = local.enable_custom_domain && local.custom_cert_arn != null ? 1 : 0

  domain_name = var.api_custom_domain

  domain_name_configuration {
    certificate_arn = local.custom_cert_arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }
}

resource "aws_apigatewayv2_api_mapping" "api" {
  count = length(aws_apigatewayv2_domain_name.api) > 0 ? 1 : 0

  api_id      = aws_apigatewayv2_api.http.id
  domain_name = aws_apigatewayv2_domain_name.api[0].id
  stage       = aws_apigatewayv2_stage.default.id
}

resource "aws_route53_record" "api_alias" {
  count = local.use_route53_acm && length(aws_apigatewayv2_domain_name.api) > 0 ? 1 : 0

  zone_id = var.route53_zone_id
  name    = var.api_custom_domain
  type    = "A"

  alias {
    name                   = aws_apigatewayv2_domain_name.api[0].domain_name_configuration[0].target_domain_name
    zone_id                = aws_apigatewayv2_domain_name.api[0].domain_name_configuration[0].hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "api_alias_ipv6" {
  count = local.use_route53_acm && length(aws_apigatewayv2_domain_name.api) > 0 ? 1 : 0

  zone_id = var.route53_zone_id
  name    = var.api_custom_domain
  type    = "AAAA"

  alias {
    name                   = aws_apigatewayv2_domain_name.api[0].domain_name_configuration[0].target_domain_name
    zone_id                = aws_apigatewayv2_domain_name.api[0].domain_name_configuration[0].hosted_zone_id
    evaluate_target_health = false
  }
}

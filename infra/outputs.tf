# Outputs for AI Requirements Quality Evaluator infrastructure

# URL Outputs
output "api_url" {
  description = "API Gateway endpoint URL"
  value       = aws_apigatewayv2_api.api.api_endpoint
}

output "api_evaluate_url" {
  description = "Full URL for the /evaluate endpoint"
  value       = "${aws_apigatewayv2_api.api.api_endpoint}/evaluate"
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "cloudfront_url" {
  description = "Full CloudFront URL for the frontend"
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

# Resource Names/IDs
output "dynamodb_table_name" {
  description = "DynamoDB table name for rate limiting"
  value       = aws_dynamodb_table.rate_limit.name
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.evaluator.function_name
}

output "lambda_function_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.evaluator.arn
}

output "frontend_bucket_name" {
  description = "S3 bucket name for frontend assets"
  value       = aws_s3_bucket.frontend.id
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.frontend.id
}

# Configuration Outputs
output "bedrock_model_id" {
  description = "Bedrock model ID configured for evaluations"
  value       = var.bedrock_model_id
}

output "bedrock_region" {
  description = "AWS region where Bedrock is accessed"
  value       = var.aws_region
}

output "daily_rate_limit" {
  description = "Configured daily rate limit per IP"
  value       = var.daily_rate_limit
}

output "log_level" {
  description = "Configured logging level"
  value       = var.log_level
}

output "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  value       = var.lambda_timeout
}

output "bedrock_timeout" {
  description = "Bedrock API timeout in seconds"
  value       = var.bedrock_timeout
}

# CloudWatch Log Groups
output "lambda_log_group" {
  description = "CloudWatch log group for Lambda"
  value       = aws_cloudwatch_log_group.lambda_logs.name
}

output "api_log_group" {
  description = "CloudWatch log group for API Gateway"
  value       = aws_cloudwatch_log_group.api_logs.name
}

# CloudWatch Alarms
output "lambda_error_alarm" {
  description = "CloudWatch alarm for Lambda errors"
  value       = aws_cloudwatch_metric_alarm.lambda_errors.alarm_name
}

output "lambda_duration_alarm" {
  description = "CloudWatch alarm for Lambda duration"
  value       = aws_cloudwatch_metric_alarm.lambda_duration.alarm_name
}

output "api_5xx_error_alarm" {
  description = "CloudWatch alarm for API Gateway 5XX errors"
  value       = aws_cloudwatch_metric_alarm.api_5xx_errors.alarm_name
}

output "high_request_rate_alarm" {
  description = "CloudWatch alarm for high request rate"
  value       = aws_cloudwatch_metric_alarm.high_request_rate.alarm_name
}

# API Authentication
output "api_key_id" {
  description = "API Gateway API key ID"
  value       = aws_apigatewayv2_api_key.api_key.id
}

output "api_key_value" {
  description = "API Gateway API key value (store securely)"
  value       = aws_apigatewayv2_api_key.api_key.value
  sensitive   = true
}

output "usage_plan_id" {
  description = "API Gateway usage plan ID"
  value       = aws_apigatewayv2_usage_plan.api.id
}

# Deployment Information
output "deployment_summary" {
  description = "Summary of deployed resources and configuration"
  value = {
    frontend_url          = "https://${aws_cloudfront_distribution.frontend.domain_name}"
    api_endpoint          = "${aws_apigatewayv2_api.api.api_endpoint}/evaluate"
    region                = var.aws_region
    environment           = var.environment
    bedrock_model         = var.bedrock_model_id
    daily_rate_limit      = var.daily_rate_limit
    lambda_timeout        = var.lambda_timeout
    bedrock_timeout       = var.bedrock_timeout
    log_level             = var.log_level
    model_temperature     = var.model_temperature
    model_max_tokens      = var.model_max_tokens
  }
}

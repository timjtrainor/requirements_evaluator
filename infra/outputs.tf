# Outputs for AI Requirements Quality Evaluator infrastructure

output "api_url" {
  description = "API Gateway endpoint URL"
  value       = aws_apigatewayv2_api.api.api_endpoint
}

output "api_evaluate_url" {
  description = "Full URL for the /evaluate endpoint"
  value       = "${aws_apigatewayv2_api.api.api_endpoint}/evaluate"
}

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

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "cloudfront_url" {
  description = "Full CloudFront URL for the frontend"
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

output "bedrock_model_id" {
  description = "Bedrock model ID configured for evaluations"
  value       = var.bedrock_model_id
}

output "bedrock_region" {
  description = "AWS region where Bedrock is accessed"
  value       = var.aws_region
}

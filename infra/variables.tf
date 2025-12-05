# Variables for AI Requirements Quality Evaluator infrastructure

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "requirements-evaluator"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "bedrock_model_id" {
  description = "Amazon Bedrock model ID to use for evaluations"
  type        = string
  default     = "anthropic.claude-3-haiku-20240307-v1:0"
}

variable "daily_rate_limit" {
  description = "Maximum number of API requests per IP per day"
  type        = number
  default     = 50
}

variable "log_level" {
  description = "Logging level for Lambda function"
  type        = string
  default     = "INFO"
}

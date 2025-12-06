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
  description = <<-EOT
    Amazon Bedrock model ID to use for evaluations.
    
    The application is model-agnostic and can work with different foundation models
    available through Amazon Bedrock. The model ID can be overridden at deployment time.
    
    Default: openai.gpt-oss-120b-1:0
    
    Other supported models include:
    - anthropic.claude-3-haiku-20240307-v1:0 (fast, cost-effective)
    - anthropic.claude-3-sonnet-20240229-v1:0 (balanced performance)
    - anthropic.claude-3-opus-20240229-v1:0 (highest capability)
    - Other OpenAI and foundation models available in your Bedrock region
    
    Trade-offs when switching models:
    - Cost: Different models have different pricing (e.g., Haiku is cheaper than Opus)
    - Performance: Larger models may provide more accurate evaluations
    - Speed: Smaller models typically respond faster
    - Availability: Ensure the model is enabled in your Bedrock region
    
    To override: terraform apply -var="bedrock_model_id=anthropic.claude-3-haiku-20240307-v1:0"
  EOT
  type        = string
  default     = "openai.gpt-oss-120b-1:0"
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

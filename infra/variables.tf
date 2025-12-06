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
  
  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], var.log_level)
    error_message = "log_level must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL"
  }
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds (max 900)"
  type        = number
  default     = 30
  
  validation {
    condition     = var.lambda_timeout >= 5 && var.lambda_timeout <= 900
    error_message = "lambda_timeout must be between 5 and 900 seconds"
  }
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB (128-10240)"
  type        = number
  default     = 256
  
  validation {
    condition     = var.lambda_memory_size >= 128 && var.lambda_memory_size <= 10240
    error_message = "lambda_memory_size must be between 128 and 10240 MB"
  }
}

variable "bedrock_timeout" {
  description = "Bedrock API call timeout in seconds"
  type        = number
  default     = 30
  
  validation {
    condition     = var.bedrock_timeout >= 5 && var.bedrock_timeout <= 120
    error_message = "bedrock_timeout must be between 5 and 120 seconds"
  }
}

variable "model_temperature" {
  description = "Model temperature for consistent evaluations (0.0-1.0)"
  type        = number
  default     = 0.2
  
  validation {
    condition     = var.model_temperature >= 0.0 && var.model_temperature <= 1.0
    error_message = "model_temperature must be between 0.0 and 1.0"
  }
}

variable "model_max_tokens" {
  description = "Maximum tokens in model response"
  type        = number
  default     = 1024
  
  validation {
    condition     = var.model_max_tokens >= 256 && var.model_max_tokens <= 4096
    error_message = "model_max_tokens must be between 256 and 4096"
  }
}

variable "min_requirement_length" {
  description = "Minimum requirement text length in characters"
  type        = number
  default     = 10
  
  validation {
    condition     = var.min_requirement_length >= 1 && var.min_requirement_length <= 100
    error_message = "min_requirement_length must be between 1 and 100 characters"
  }
}

variable "max_requirement_length" {
  description = "Maximum requirement text length in characters"
  type        = number
  default     = 5000
  
  validation {
    condition     = var.max_requirement_length >= 100 && var.max_requirement_length <= 50000
    error_message = "max_requirement_length must be between 100 and 50000 characters"
  }
}

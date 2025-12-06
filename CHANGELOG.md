# Changelog

All notable changes to the AI Requirements Quality Evaluator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Pydantic-based configuration validation with fail-fast behavior
- Structured JSON logging throughout backend for better observability
- Comprehensive Terraform variable parameterization
- Additional configuration parameters (timeouts, model temperature, token limits)
- Enhanced error context in logs including model ID, duration, and error details
- Terraform output for deployment summary with all runtime configuration
- Version pinning for AWS provider and dependencies

### Changed
- Upgraded configuration management to use Pydantic v2 for validation
- Updated all modules to use singleton config pattern
- Enhanced schema validation using Pydantic models
- Improved error handling with structured logging
- Updated Lambda timeout configuration to be parameterizable
- Updated Bedrock timeout configuration to be parameterizable

### Fixed
- Configuration validation now properly validates all input parameters
- Logging now includes structured context for debugging

## [0.1.0] - 2024-12-06

### Added
- Initial release of AI Requirements Quality Evaluator
- Model-agnostic architecture supporting multiple Bedrock models
- Support for OpenAI and Anthropic Claude models via Amazon Bedrock
- Rate limiting using DynamoDB (50 requests per IP per day)
- CloudFront + S3 static frontend hosting
- API Gateway HTTP API for evaluation endpoint
- Lambda function for requirement evaluation
- Comprehensive documentation for model selection
- Evaluation harness for testing AI quality
- Configuration module for centralized settings

### Features
- Ambiguity detection in requirements
- Testability assessment
- Completeness scoring (1-10 scale)
- Specific issue identification
- Improvement suggestions
- JSON schema validation for AI responses

### Infrastructure
- Terraform configuration for full AWS deployment
- DynamoDB table for rate limiting
- CloudWatch logs for Lambda and API Gateway
- IAM roles with least-privilege permissions
- CORS-enabled API Gateway
- CloudFront distribution with S3 origin

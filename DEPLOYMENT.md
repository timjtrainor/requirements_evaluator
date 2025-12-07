# Deployment and Validation Guide

This guide covers deploying the enhanced AI Requirements Quality Evaluator and validating all improvements.

## Prerequisites

Before deploying:

1. **AWS Account**: With appropriate permissions for Lambda, API Gateway, DynamoDB, S3, CloudFront, and Bedrock
2. **Terraform**: Version >= 1.0 installed
3. **Python**: Version 3.11+ installed
4. **Bedrock Access**: Model access enabled in your AWS region

## Pre-Deployment Validation

### 1. Run Tests Locally

```bash
cd backend

# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-cov black flake8 bandit mypy

# Run unit tests
python -m unittest discover -s . -p 'test_*.py' -v

# Run with coverage
pytest --cov=. --cov-report=term test_*.py

# Expected: All tests pass (37+ tests)
```

### 2. Run Linters and Security Checks

```bash
cd backend

# Code formatting check
black --check .

# Linting
flake8 .

# Security scan
bandit -r .

# Type checking
mypy --ignore-missing-imports .

# Expected: No critical issues
```

### 3. Validate Terraform Configuration

```bash
cd infra

# Format check
terraform fmt -check -recursive

# Initialize
terraform init

# Validate
terraform validate

# Expected: Configuration is valid!
```

## Deployment Steps

### 1. Configure Terraform Variables

Create `infra/terraform.tfvars`:

```hcl
# Project configuration
project_name     = "requirements-evaluator"
environment      = "prod"  # or "dev", "staging"
aws_region       = "us-east-1"

# Model configuration
bedrock_model_id = "anthropic.claude-3-sonnet-20240229-v1:0"  # or your preferred model

# Rate limiting
daily_rate_limit = 100  # Adjust based on expected usage

# Performance tuning
lambda_timeout   = 30
bedrock_timeout  = 30
lambda_memory_size = 256

# Model parameters
model_temperature = 0.2
model_max_tokens  = 1024

# Logging
log_level = "INFO"  # Use "DEBUG" for development
```

### 2. Deploy Infrastructure

```bash
cd infra

# Review the plan
terraform plan

# Deploy
terraform apply

# Save outputs
terraform output -json > ../deployment-outputs.json
```

### 3. Upload Frontend Assets

```bash
# Get bucket name from Terraform
BUCKET_NAME=$(cd infra && terraform output -raw frontend_bucket_name)

# Upload frontend files
aws s3 sync frontend/ s3://$BUCKET_NAME/

# Verify upload
aws s3 ls s3://$BUCKET_NAME/
```

### 4. Invalidate CloudFront Cache

```bash
# Get distribution ID
DIST_ID=$(cd infra && terraform output -raw cloudfront_distribution_id)

# Invalidate cache
aws cloudfront create-invalidation --distribution-id $DIST_ID --paths "/*"
```

## Post-Deployment Validation

### 1. Verify Infrastructure

```bash
# Get deployment summary
cd infra
terraform output deployment_summary

# Check Lambda function
FUNCTION_NAME=$(terraform output -raw lambda_function_name)
aws lambda get-function --function-name $FUNCTION_NAME

# Check DynamoDB table
TABLE_NAME=$(terraform output -raw dynamodb_table_name)
aws dynamodb describe-table --table-name $TABLE_NAME
```

### 2. Test API Endpoint

```bash
# Get API URL
API_URL=$(cd infra && terraform output -raw api_evaluate_url)

# Test evaluation
curl -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d '{
    "requirementText": "The system shall respond within 2 seconds under normal load."
  }'

# Expected: JSON response with evaluation results
```

### 3. Test Frontend

```bash
# Get CloudFront URL
FRONTEND_URL=$(cd infra && terraform output -raw cloudfront_url)

echo "Access the frontend at: $FRONTEND_URL"

# Open in browser and test:
# - Input validation (too short, too long)
# - Evaluation with sample requirement
# - Tooltips on metric labels
# - Feedback buttons
# - Error handling (invalid input)
```

### 4. Verify Logging

```bash
# Get log group name
LOG_GROUP=$(cd infra && terraform output -raw lambda_log_group)

# View recent logs
aws logs tail $LOG_GROUP --follow

# Expected: Structured JSON logs with:
# - timestamp
# - level
# - message
# - model_id
# - duration_seconds
# - request_id
```

### 5. Test Configuration Validation

```bash
# Try invalid configuration (should fail)
cd backend

# Test with invalid timeout
export BEDROCK_TIMEOUT=200
python -c "from config import get_config; get_config()"

# Expected: Exit with validation error

# Test with valid config
export BEDROCK_TIMEOUT=30
python -c "from config import get_config; c = get_config(); print(f'Config valid: {c.bedrock_timeout}s')"

# Expected: Config valid: 30s
```

## Monitoring Setup

### 1. Create CloudWatch Alarms

```bash
# Lambda errors
aws cloudwatch put-metric-alarm \
  --alarm-name requirements-evaluator-errors \
  --alarm-description "Alert on Lambda errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=FunctionName,Value=$FUNCTION_NAME

# Lambda duration
aws cloudwatch put-metric-alarm \
  --alarm-name requirements-evaluator-duration \
  --alarm-description "Alert on high Lambda duration" \
  --metric-name Duration \
  --namespace AWS/Lambda \
  --statistic Average \
  --period 300 \
  --threshold 15000 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=FunctionName,Value=$FUNCTION_NAME
```

### 2. Set Up Cost Alerts

```bash
# Create budget alert for $50/month
aws budgets create-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget '{
    "BudgetName": "requirements-evaluator-budget",
    "BudgetLimit": {
      "Amount": "50",
      "Unit": "USD"
    },
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST"
  }'
```

## Validation Checklist

- [ ] All unit tests pass (37+ tests)
- [ ] No linting errors from flake8
- [ ] No security issues from bandit
- [ ] Terraform validation passes
- [ ] Infrastructure deployed successfully
- [ ] Lambda function is active
- [ ] DynamoDB table exists
- [ ] CloudFront distribution is deployed
- [ ] API endpoint returns valid responses
- [ ] Frontend loads in browser
- [ ] Tooltips display on hover
- [ ] Feedback buttons work
- [ ] Structured logs visible in CloudWatch
- [ ] Configuration validation works
- [ ] CloudWatch alarms created
- [ ] Cost budget alerts configured

## Testing Different Models

To test with different Bedrock models:

```bash
# Update Terraform variable
cd infra

# Test with Claude Haiku (fast, cheap)
terraform apply -var="bedrock_model_id=anthropic.claude-3-haiku-20240307-v1:0"

# Test with Claude Sonnet (balanced)
terraform apply -var="bedrock_model_id=anthropic.claude-3-sonnet-20240229-v1:0"

# Run eval harness to compare
cd ../backend
export BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
python eval_harness.py > haiku-results.txt

export BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
python eval_harness.py > sonnet-results.txt

# Compare results
diff haiku-results.txt sonnet-results.txt
```

## Troubleshooting

### Lambda Errors

```bash
# View recent errors
aws logs filter-log-events \
  --log-group-name $LOG_GROUP \
  --filter-pattern '"level":"ERROR"' \
  --max-items 10

# Check function configuration
aws lambda get-function-configuration --function-name $FUNCTION_NAME
```

### Rate Limiting Issues

```bash
# Check DynamoDB table
aws dynamodb scan --table-name $TABLE_NAME

# Clear rate limits for an IP
aws dynamodb delete-item \
  --table-name $TABLE_NAME \
  --key '{"pk": {"S": "IP#1.2.3.4"}}'
```

### Frontend Not Loading

```bash
# Check S3 bucket contents
aws s3 ls s3://$BUCKET_NAME/

# Check CloudFront distribution status
aws cloudfront get-distribution --id $DIST_ID \
  --query 'Distribution.Status'

# Expected: "Deployed"
```

### Bedrock Access Denied

1. Go to [Bedrock Console](https://console.aws.amazon.com/bedrock)
2. Navigate to "Model access"
3. Request access to your model
4. Wait for approval (usually immediate)
5. Verify IAM permissions include `bedrock:InvokeModel`

## Performance Benchmarks

Expected performance metrics:

| Metric | Target | Notes |
|--------|--------|-------|
| Lambda Cold Start | < 3s | First invocation |
| Lambda Warm Start | < 1s | Subsequent invocations |
| Bedrock Call | 2-5s | Depends on model |
| Total API Latency | < 10s | End-to-end |
| Frontend Load | < 2s | Static assets |

Monitor these in CloudWatch to ensure optimal performance.

## Security Validation

```bash
# Check Lambda IAM role permissions
aws iam get-role-policy \
  --role-name requirements-evaluator-lambda-role-prod \
  --policy-name requirements-evaluator-lambda-bedrock-prod

# Check S3 bucket is not public
aws s3api get-public-access-block \
  --bucket $BUCKET_NAME

# Expected: All blocks enabled
```

## Rollback Procedure

If issues occur:

```bash
# Rollback Terraform
cd infra
terraform plan -destroy
terraform destroy

# Or rollback to previous state
terraform state pull > current-state.json
# Restore from backup
terraform state push previous-state.json
```

## Next Steps

After successful deployment:

1. Monitor CloudWatch logs for errors
2. Track Bedrock costs in Cost Explorer
3. Collect user feedback via feedback buttons
4. Review evaluation accuracy with eval harness
5. Consider fine-tuning prompts based on feedback
6. Set up automated backups for DynamoDB
7. Configure CloudTrail for audit logging
8. Enable AWS Config for compliance checking

## Support

For issues:
1. Check CloudWatch logs
2. Review SECURITY.md for best practices
3. Consult API_SCHEMA.md for API details
4. Check SUPPORTED_MODELS.md for model info

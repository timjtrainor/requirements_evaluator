# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability in the AI Requirements Quality Evaluator, please report it by emailing the maintainers. Please do not create public GitHub issues for security vulnerabilities.

Include the following information:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

## Security Best Practices

### Configuration Security

1. **Environment Variables**: Never commit sensitive values to version control
   - Use AWS Secrets Manager or Systems Manager Parameter Store for sensitive data
   - Configure via Terraform or environment-specific `.tfvars` files (git-ignored)

2. **API Keys and Tokens**: 
   - Bedrock access is via IAM roles, not API keys
   - No API keys should be stored in environment variables
   - Use temporary credentials when possible

3. **Rate Limiting**:
   - Default: 50 requests per IP per day
   - Increase cautiously to prevent abuse
   - Monitor CloudWatch logs for suspicious patterns

### Infrastructure Security

1. **IAM Permissions**:
   - Lambda uses least-privilege IAM roles
   - Bedrock access scoped to specific model ARN
   - DynamoDB access limited to rate limit table

2. **Network Security**:
   - API Gateway uses HTTPS only
   - CloudFront enforces TLS 1.2+
   - No direct internet access from Lambda

3. **S3 Security**:
   - Frontend bucket blocks all public access
   - Access only via CloudFront with Origin Access Control
   - No direct S3 URLs exposed

### Application Security

1. **Input Validation**:
   - Strict length limits on requirement text (10-5000 chars)
   - JSON schema validation on all inputs
   - Pydantic validation with fail-fast behavior

2. **Output Sanitization**:
   - All model responses validated against schema
   - No user input echoed without validation
   - CORS headers properly configured

3. **Error Handling**:
   - No internal details exposed in error messages
   - Structured logging for debugging
   - Generic error messages to clients

### Monitoring and Alerts

1. **CloudWatch Logs**:
   - All requests logged with structured JSON
   - Errors include context without sensitive data
   - 14-day retention configured

2. **Recommended Alarms** (not auto-created):
   ```terraform
   # Add to your Terraform configuration
   resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
     alarm_name          = "requirements-evaluator-errors"
     comparison_operator = "GreaterThanThreshold"
     evaluation_periods  = "2"
     metric_name         = "Errors"
     namespace           = "AWS/Lambda"
     period              = "300"
     statistic           = "Sum"
     threshold           = "10"
     alarm_description   = "Alert on Lambda errors"
     dimensions = {
       FunctionName = aws_lambda_function.evaluator.function_name
     }
   }
   ```

3. **Cost Monitoring**:
   - Set up AWS Budget alerts
   - Monitor Bedrock costs via Cost Explorer
   - Track Lambda invocation count

### Timeout Configuration

1. **Lambda Timeout**: 30 seconds (default)
   - Prevents runaway costs from long-running functions
   - Configurable via `lambda_timeout` variable

2. **Bedrock Timeout**: 30 seconds (default)
   - Prevents hanging on model calls
   - Configurable via `bedrock_timeout` variable

3. **API Gateway Timeout**: 30 seconds (hard limit)
   - Cannot be extended beyond 30 seconds
   - Lambda must complete within this window

### Secrets Management

Currently, the application uses:
- **IAM Roles** for AWS service authentication (recommended)
- **Environment Variables** for non-sensitive configuration

For sensitive configuration in future versions:

1. **AWS Secrets Manager** (recommended for secrets):
   ```python
   import boto3
   
   secrets_client = boto3.client('secretsmanager')
   secret = secrets_client.get_secret_value(SecretId='prod/api-key')
   ```

2. **SSM Parameter Store** (recommended for config):
   ```python
   import boto3
   
   ssm = boto3.client('ssm')
   param = ssm.get_parameter(Name='/prod/config/rate-limit', WithDecryption=True)
   ```

### Dependency Security

1. **Version Pinning**:
   - All dependencies use version constraints
   - Terraform provider versions pinned
   - Python packages use semantic versioning

2. **Dependency Scanning**:
   - Use `pip-audit` to check for vulnerabilities:
     ```bash
     pip install pip-audit
     pip-audit -r backend/requirements.txt
     ```

3. **Regular Updates**:
   - Review and update dependencies quarterly
   - Monitor GitHub security advisories
   - Test updates in development environment first

### Security Checklist for Deployment

Before deploying to production:

- [ ] Review IAM policies for least privilege
- [ ] Ensure all S3 buckets block public access
- [ ] Verify CloudFront uses TLS 1.2+
- [ ] Set appropriate rate limits
- [ ] Configure CloudWatch alarms
- [ ] Set up AWS Budget alerts
- [ ] Review and rotate any credentials
- [ ] Enable AWS CloudTrail for audit logging
- [ ] Configure VPC Flow Logs if using VPC
- [ ] Review security group rules
- [ ] Enable AWS GuardDuty for threat detection
- [ ] Configure AWS Config for compliance
- [ ] Set up backup and disaster recovery

### Known Security Considerations

1. **Public API**:
   - The /evaluate endpoint is publicly accessible
   - Protected only by rate limiting
   - Consider adding authentication for production use

2. **Rate Limiting Storage**:
   - IP addresses stored in DynamoDB
   - Consider privacy implications
   - No PII beyond IP address is stored

3. **Model Responses**:
   - AI-generated content not guaranteed to be safe
   - Validate all model outputs before displaying
   - Current implementation validates structure only

### Code Quality and Security Tools

Run security checks before committing:

```bash
# Install tools
pip install bandit safety

# Run security scan
bandit -r backend/

# Check for known vulnerabilities
safety check -r backend/requirements.txt

# Run pre-commit hooks
pre-commit run --all-files
```

### Terraform Security

1. **State File Security**:
   - Never commit `.tfstate` files
   - Use S3 backend with encryption:
     ```terraform
     terraform {
       backend "s3" {
         bucket         = "my-terraform-state"
         key            = "requirements-evaluator/terraform.tfstate"
         region         = "us-east-1"
         encrypt        = true
         dynamodb_table = "terraform-locks"
       }
     }
     ```

2. **tfvars Files**:
   - Add `*.tfvars` to `.gitignore`
   - Store production values in Secrets Manager
   - Use workspaces for environment separation

### Compliance Considerations

For regulated industries:

1. **Data Residency**: 
   - Choose AWS region based on requirements
   - Bedrock models stay in configured region

2. **Audit Logging**:
   - Enable CloudTrail for all API calls
   - Configure log retention per compliance needs

3. **Encryption**:
   - All data encrypted in transit (TLS)
   - DynamoDB encryption at rest available
   - S3 encryption at rest available

### Incident Response

If a security incident occurs:

1. **Immediate Actions**:
   - Disable the affected component
   - Rotate any compromised credentials
   - Review CloudWatch logs for extent of impact

2. **Investigation**:
   - Check CloudTrail for unauthorized actions
   - Review application logs
   - Identify root cause

3. **Remediation**:
   - Apply security patches
   - Update vulnerable dependencies
   - Strengthen affected security controls

4. **Post-Incident**:
   - Document lessons learned
   - Update security procedures
   - Communicate with stakeholders

## Security Updates

This document will be updated as new security considerations are identified or as the application evolves.

Last updated: 2024-12-06

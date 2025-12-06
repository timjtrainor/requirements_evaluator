# AI Requirements Quality Evaluator

A serverless application that evaluates software requirements using Amazon Bedrock AI. The application analyzes requirements for **ambiguity**, **testability**, and **completeness**, providing structured feedback and improvement suggestions.

## Overview

This project demonstrates AI reliability thinking by using Amazon Bedrock AI to analyze software requirements. It evaluates:

- **Ambiguity**: Identifies vague, unclear, or subjective language
- **Testability**: Assesses whether the requirement has measurable acceptance criteria
- **Completeness**: Scores how complete the requirement is (1-10 scale)
- **Issues & Suggestions**: Provides specific feedback for improvement

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   CloudFront    │────▶│   API Gateway   │────▶│     Lambda      │
│   + S3 Static   │     │    (HTTP API)   │     │   (Python)      │
│     Frontend    │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                        ┌─────────────────┐              │
                        │    DynamoDB     │◀─────────────┤
                        │  (Rate Limit)   │              │
                        └─────────────────┘              │
                                                         │
                        ┌─────────────────┐              │
                        │ Amazon Bedrock  │◀─────────────┘
                        │   (AI Model)    │
                        └─────────────────┘
```

### Components

- **Frontend**: Static HTML/CSS/JS served via S3 + CloudFront
- **API Gateway**: HTTP API handling POST /evaluate requests
- **Lambda**: Python function that validates input, checks rate limits, and calls Bedrock
- **DynamoDB**: Stores daily request counts per IP for rate limiting
- **Bedrock**: AI model for requirement analysis (configurable)

## Project Structure

```
requirements_evaluator/
├── frontend/               # Static web UI
│   ├── index.html         # Main HTML file
│   ├── styles.css         # Styles
│   └── app.js             # Frontend JavaScript
│
├── backend/               # Lambda function code (Python)
│   ├── handler.py         # Main Lambda handler
│   ├── rate_limit.py      # DynamoDB rate limiting
│   ├── eval_harness.py    # Evaluation testing harness
│   ├── eval_dataset.json  # Sample evaluation dataset
│   └── requirements.txt   # Python dependencies
│
├── infra/                 # Terraform infrastructure
│   ├── main.tf            # Main Terraform configuration
│   ├── variables.tf       # Variable definitions
│   └── outputs.tf         # Output definitions
│
├── README.md
└── .gitignore
```

## Setup Instructions

### Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform >= 1.0
- Python 3.11+
- Access to Amazon Bedrock with Claude 3 Haiku model enabled

### 1. Enable Amazon Bedrock Model Access

1. Go to the [Amazon Bedrock Console](https://console.aws.amazon.com/bedrock)
2. Navigate to "Model access"
3. Request access to your desired model (default: OpenAI GPT-120B or Claude 3 Haiku)
4. Wait for access approval (usually immediate)

### 2. Deploy Infrastructure with Terraform

```bash
cd infra

# Initialize Terraform
terraform init

# Review the plan
terraform plan

# Deploy (this will create all AWS resources)
terraform apply
```

Save the outputs - you'll need them for configuring the frontend.

### 3. Configure the Frontend

Edit `frontend/app.js` and update the `CONFIG.API_BASE_URL`:

```javascript
const CONFIG = {
    API_BASE_URL: 'https://your-cloudfront-domain.cloudfront.net',
    EVALUATE_ENDPOINT: '/evaluate'
};
```

### 4. Upload Frontend Assets

```bash
# Get the bucket name from Terraform output
BUCKET_NAME=$(terraform output -raw frontend_bucket_name)

# Upload frontend files
aws s3 sync ../frontend/ s3://$BUCKET_NAME/
```

### 5. Access the Application

Get the CloudFront URL:

```bash
terraform output cloudfront_url
```

## Lambda Configuration

The Lambda function uses these environment variables (set by Terraform):

| Variable | Description | Default |
|----------|-------------|---------|
| `RATE_LIMIT_TABLE` | DynamoDB table name | Auto-generated |
| `DAILY_RATE_LIMIT` | Max requests per IP per day | 50 |
| `BEDROCK_REGION` | AWS region for Bedrock | us-east-1 |
| `BEDROCK_MODEL_ID` | Bedrock model ID | openai.gpt-oss-120b-1:0 |
| `LOG_LEVEL` | Logging level | INFO |

## Model Configuration

### Overview

The AI Requirements Evaluator is **model-agnostic** and designed to work with different Amazon Bedrock foundation models. The application uses Amazon Bedrock's unified API, which allows seamless switching between different AI models without code changes.

### Default Model

**Model ID**: `openai.gpt-oss-120b-1:0`  
**Provider**: OpenAI (via Amazon Bedrock)  
**Characteristics**: 120B parameter model providing balanced performance and cost

This model is selected as the default because it offers:
- Good balance of performance and cost
- Consistent JSON output formatting
- Reliable requirement analysis capabilities
- Wide availability across AWS regions

### Architecture: Model-Agnostic Design

The application is architected to be model-agnostic through:

1. **Configuration Abstraction**: The `backend/config.py` module serves as a single source of truth for all configuration, including model selection.

2. **Unified Interface**: All Bedrock models use the same API structure, allowing transparent model switching.

3. **Schema Validation**: Response validation ensures consistent output format regardless of the underlying model.

4. **Environment-Based Configuration**: Model selection is controlled via environment variables, not hard-coded.

### Supported Models

The application can work with any Bedrock model that supports structured JSON output. Popular options include:

#### OpenAI Models (via Bedrock)
- `openai.gpt-oss-120b-1:0` - Default, 120B parameters
- Other OpenAI models available in your region

#### Anthropic Claude Models
- `anthropic.claude-3-haiku-20240307-v1:0` - Fast, cost-effective (fastest response time)
- `anthropic.claude-3-sonnet-20240229-v1:0` - Balanced performance (recommended for production)
- `anthropic.claude-3-opus-20240229-v1:0` - Highest capability (best accuracy)

### How to Override the Model

#### Option 1: Terraform Variable (Recommended)

When deploying infrastructure:

```bash
cd infra

# Override at apply time
terraform apply -var="bedrock_model_id=anthropic.claude-3-haiku-20240307-v1:0"

# Or create a terraform.tfvars file
echo 'bedrock_model_id = "anthropic.claude-3-sonnet-20240229-v1:0"' > terraform.tfvars
terraform apply
```

#### Option 2: Environment Variable (Lambda)

Update the Lambda function's environment variables directly:

```bash
aws lambda update-function-configuration \
  --function-name requirements-evaluator-dev \
  --environment "Variables={BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0,BEDROCK_REGION=us-east-1,...}"
```

#### Option 3: Terraform Variable File

Create `infra/terraform.tfvars`:

```hcl
bedrock_model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
aws_region       = "us-east-1"
```

Then apply:

```bash
terraform apply
```

#### Option 4: For Local Testing (Eval Harness)

When running the evaluation harness locally:

```bash
cd backend
export BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
export BEDROCK_REGION=us-east-1
python eval_harness.py
```

### Trade-offs When Switching Models

Consider these factors when choosing a different model:

#### Cost

| Model | Input Cost (per 1K tokens) | Output Cost (per 1K tokens) | Relative Cost |
|-------|---------------------------|----------------------------|---------------|
| Claude 3 Haiku | $0.00025 | $0.00125 | Lowest |
| OpenAI GPT-120B | ~$0.0005 | ~$0.0015 | Medium |
| Claude 3 Sonnet | $0.003 | $0.015 | Higher |
| Claude 3 Opus | $0.015 | $0.075 | Highest |

**Impact**: For a typical evaluation (200 input + 400 output tokens):
- Haiku: ~$0.0006 per evaluation
- Sonnet: ~$0.007 per evaluation  
- Opus: ~$0.033 per evaluation

#### Performance & Accuracy

- **Haiku**: Fast, reliable for straightforward evaluations. May miss nuanced issues.
- **GPT-120B**: Balanced performance, good at following JSON schemas.
- **Sonnet**: Better at detecting subtle ambiguities and edge cases. Recommended for critical applications.
- **Opus**: Highest accuracy, best for complex requirements. May provide more detailed feedback.

#### Response Time

- **Haiku**: ~1-2 seconds typical response time
- **GPT-120B**: ~2-3 seconds typical response time
- **Sonnet**: ~3-5 seconds typical response time
- **Opus**: ~5-10 seconds typical response time

#### Availability

- Ensure the chosen model has been enabled in the [Amazon Bedrock Console](https://console.aws.amazon.com/bedrock) under "Model access"
- Model availability varies by AWS region
- Some models may require requesting access and waiting for approval

### Model Access Requirements

Before switching models:

1. **Enable Model Access**: 
   - Go to Amazon Bedrock Console → Model access
   - Request access to the desired model
   - Wait for approval (usually immediate for Claude models)

2. **Update IAM Permissions**:
   - The Terraform configuration automatically grants permission to the specified model
   - If changing models post-deployment, ensure the Lambda IAM role has `bedrock:InvokeModel` permission for the new model ARN

3. **Update Regional Availability**:
   - Verify the model is available in your configured `aws_region`
   - Some models are only available in specific regions (us-east-1, us-west-2, etc.)

### Validation & Error Handling

The application includes robust validation for model responses:

- **Schema Validation**: All model responses are validated against the expected JSON schema
- **Type Checking**: Field types are verified (boolean, string, integer, array)
- **Range Validation**: Completeness scores are checked to be between 1-10
- **Graceful Degradation**: If a model returns invalid JSON, the system returns a structured error response

This ensures reliability even if different models format responses slightly differently.

### Monitoring Model Performance

When switching models, monitor these metrics:

1. **CloudWatch Logs**: Check Lambda logs for schema validation warnings
2. **Response Times**: Monitor Lambda duration metrics
3. **Error Rates**: Track failed evaluations in CloudWatch
4. **Cost**: Review AWS Cost Explorer for Bedrock charges

### Best Practices

1. **Start with Haiku**: Use Claude 3 Haiku for development and testing due to low cost and speed
2. **Production**: Consider Sonnet for production workloads requiring better accuracy
3. **Testing**: Run the eval harness with different models to compare accuracy:
   ```bash
   BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0 python eval_harness.py
   BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0 python eval_harness.py
   ```
4. **Regional Selection**: Use us-east-1 for widest model availability
5. **Version Pinning**: Use specific model versions (not aliases) for consistency



## API Reference

### POST /evaluate

Evaluates a software requirement.

**Request:**
```json
{
    "requirementText": "The system shall allow users to log in within 3 seconds."
}
```

**Response:**
```json
{
    "ambiguity_detected": false,
    "ambiguity_details": "The requirement is clear with specific time constraint.",
    "testable": true,
    "testability_details": "The 3-second response time provides a measurable criterion.",
    "completeness_score": 7,
    "completeness_details": "Missing error handling and security details.",
    "issues": [
        "No error handling specified",
        "Authentication method not defined"
    ],
    "suggestions": [
        "Add error handling for failed login attempts",
        "Specify the authentication mechanism (email/password, SSO, etc.)"
    ]
}
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 400 | Invalid request (missing/invalid requirementText) |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

## Running the Evaluation Harness

The eval harness tests the AI evaluator against a labeled dataset:

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export BEDROCK_REGION=us-east-1
export BEDROCK_MODEL_ID=openai.gpt-oss-120b-1:0

# Run evaluation
python eval_harness.py

# Save detailed results to file
EVAL_OUTPUT=results.json python eval_harness.py
```

The harness computes:
- **Accuracy**: Percentage of correct predictions
- **Precision/Recall**: For ambiguity and testability detection
- **FP/FN rates**: False positive and false negative counts
- **Completeness threshold accuracy**: How often the score is within threshold

## Cost and Safety Notes

### Cost Considerations

- **Lambda**: Pay per invocation and duration (~$0.0000002 per request)
- **API Gateway**: $1.00 per million requests
- **DynamoDB**: Pay per request (~$1.25 per million writes)
- **Bedrock**: Cost varies by model (see Model Configuration section)
- **S3 + CloudFront**: Minimal for static hosting

**Estimated cost**: ~$0.001-0.03 per evaluation depending on model choice

See the [Model Configuration](#model-configuration) section for detailed cost comparisons.

### Safety Measures

- **Rate Limiting**: Daily limit per IP prevents abuse
- **Input Validation**: Rejects empty or overly long inputs
- **Error Handling**: Graceful error responses without exposing internals
- **Fail Open**: Rate limiting fails open to avoid blocking legitimate requests

## AI Reliability Thinking

This project demonstrates several AI reliability patterns:

1. **Structured Output**: Uses a JSON schema to get consistent, parseable responses from the AI model

2. **Low Temperature**: Uses temperature=0.2 for more deterministic, consistent evaluations

3. **Clear Prompting**: The evaluation prompt provides explicit guidelines and examples

4. **Evaluation Harness**: The `eval_harness.py` script allows systematic testing of AI quality:
   - Measures accuracy against labeled samples
   - Computes precision/recall for binary classifications
   - Tracks completeness score accuracy within thresholds

5. **Graceful Degradation**: If AI response parsing fails, returns a structured error response

6. **Rate Limiting**: Prevents cost overruns and abuse

## Customization

### Changing the Rate Limit

Edit `infra/variables.tf`:

```hcl
variable "daily_rate_limit" {
  default = 100  # Change to your desired limit
}
```

### Modifying the Evaluation Prompt

Edit `backend/handler.py`, function `build_evaluation_prompt()`.

## Troubleshooting

### "Access Denied" for Bedrock

- Ensure you've requested access to your desired model in the Bedrock console
- Verify the Lambda role has the correct IAM permissions for the model ARN

### CORS Errors

- Ensure `API_BASE_URL` in `app.js` matches your CloudFront domain
- Check API Gateway CORS configuration

### Rate Limit Errors (429)

- Wait until the next day (UTC) for the limit to reset
- Or increase `daily_rate_limit` in Terraform variables

## License

MIT

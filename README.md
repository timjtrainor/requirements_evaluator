# AI Requirements Quality Evaluator

A serverless application that evaluates software requirements using Amazon Bedrock AI. The application analyzes requirements for **ambiguity**, **testability**, and **completeness**, providing structured feedback and improvement suggestions.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   CloudFront    │────▶│   API Gateway   │────▶│     Lambda      │
│   + S3 Static   │     │    (REST API)   │     │   (Node.js)     │
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
                        │  (Claude 3)     │
                        └─────────────────┘

                        ┌─────────────────┐
                        │   CloudWatch    │
                        │ (Logs/Metrics)  │
                        └─────────────────┘
```

## Features

- **AI-Powered Analysis**: Uses Amazon Bedrock (Claude 3 Sonnet) to evaluate requirements
- **Three Evaluation Dimensions**:
  - **Ambiguity**: Identifies vague or unclear language
  - **Testability**: Assesses if requirements can be objectively tested
  - **Completeness**: Evaluates if all necessary information is present
- **Actionable Suggestions**: Provides specific improvement recommendations
- **Rate Limiting**: Protects against abuse using DynamoDB-based rate limiting
- **Monitoring**: CloudWatch dashboard and alarms for operational visibility
- **Fully Serverless**: Pay-per-use infrastructure with automatic scaling

## Project Structure

```
requirements_evaluator/
├── frontend/                 # Static web application
│   ├── index.html           # Main HTML file
│   ├── styles.css           # CSS styles
│   └── app.js               # Frontend JavaScript
│
├── backend/                  # Lambda function code
│   ├── src/
│   │   ├── index.js         # Lambda handler
│   │   ├── evaluator.js     # Bedrock integration
│   │   ├── rateLimit.js     # Rate limiting logic
│   │   └── logger.js        # Logging utility
│   ├── tests/               # Unit tests
│   │   ├── handler.test.js
│   │   └── logger.test.js
│   ├── package.json
│   ├── jest.config.js
│   └── .eslintrc.cjs
│
├── infrastructure/           # AWS SAM templates
│   ├── template.yaml        # CloudFormation template
│   └── samconfig.toml       # SAM CLI configuration
│
└── README.md
```

## Prerequisites

- [AWS CLI](https://aws.amazon.com/cli/) configured with appropriate credentials
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- [Node.js 20.x](https://nodejs.org/) or later
- Access to Amazon Bedrock with Claude 3 model enabled

## Quick Start

### 1. Enable Amazon Bedrock Model Access

Before deploying, ensure you have access to the Claude 3 Sonnet model in Amazon Bedrock:

1. Go to the [Amazon Bedrock Console](https://console.aws.amazon.com/bedrock)
2. Navigate to "Model access"
3. Request access to "Claude 3 Sonnet" from Anthropic
4. Wait for access approval (usually instant)

### 2. Install Backend Dependencies

```bash
cd backend
npm install
```

### 3. Run Tests

```bash
cd backend
npm test
```

### 4. Deploy the Application

```bash
# Build the application
cd infrastructure
sam build

# Deploy to AWS (dev environment)
sam deploy --config-env dev
```

### 5. Upload Frontend Assets

After deployment, upload the frontend files to S3:

```bash
# Get the bucket name from deployment output
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name requirements-evaluator-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`FrontendBucketName`].OutputValue' \
  --output text)

# Upload frontend assets
aws s3 sync frontend/ s3://$BUCKET_NAME/
```

### 6. Configure Frontend API Endpoint

Update the `API_ENDPOINT` in the frontend to point to your CloudFront distribution:

```javascript
// frontend/app.js
const CONFIG = {
    API_ENDPOINT: 'https://your-cloudfront-domain.cloudfront.net/api/evaluate'
};
```

Then re-upload the frontend:

```bash
aws s3 sync frontend/ s3://$BUCKET_NAME/
```

### 7. Access the Application

Get the CloudFront URL from the deployment outputs:

```bash
aws cloudformation describe-stacks \
  --stack-name requirements-evaluator-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontUrl`].OutputValue' \
  --output text
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RATE_LIMIT_TABLE` | DynamoDB table name for rate limiting | Auto-generated |
| `RATE_LIMIT_MAX` | Maximum requests per window | 10 |
| `RATE_LIMIT_WINDOW` | Rate limit window in seconds | 60 |
| `BEDROCK_MODEL_ID` | Bedrock model to use | `anthropic.claude-3-sonnet-20240229-v1:0` |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARN, ERROR) | INFO |

### Deployment Parameters

Modify `infrastructure/samconfig.toml` to customize deployment:

- `Environment`: Deployment stage (dev, staging, prod)
- `RateLimitMax`: Maximum requests per rate limit window
- `RateLimitWindowSeconds`: Duration of rate limit window
- `BedrockModelId`: Amazon Bedrock model ID

## API Reference

### POST /evaluate

Evaluates a software requirement.

**Request:**

```json
{
    "requirement": "The system shall allow users to log in using their email and password within 3 seconds."
}
```

**Response:**

```json
{
    "ambiguity": {
        "score": 8,
        "feedback": "The requirement is mostly clear with specific authentication method and time constraint."
    },
    "testability": {
        "score": 9,
        "feedback": "The 3-second response time provides a measurable acceptance criterion."
    },
    "completeness": {
        "score": 7,
        "feedback": "Missing error handling scenarios and security considerations."
    },
    "suggestions": [
        "Add error handling for invalid credentials",
        "Specify password complexity requirements",
        "Define behavior for locked accounts"
    ]
}
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 400 | Invalid request (missing or invalid requirement) |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

## Development

### Running Locally

You can test the Lambda function locally using SAM:

```bash
cd infrastructure

# Start local API
sam local start-api

# Test with curl
curl -X POST http://localhost:3000/evaluate \
  -H "Content-Type: application/json" \
  -d '{"requirement": "The system shall display user profile information"}'
```

Note: Local testing requires AWS credentials configured for Bedrock access.

### Linting

```bash
cd backend
npm run lint

# Auto-fix issues
npm run lint:fix
```

### Testing

```bash
cd backend
npm test
```

## Monitoring

### CloudWatch Dashboard

A CloudWatch dashboard is automatically created with:
- Lambda invocation count
- Lambda errors
- Lambda duration
- API Gateway request count

Access the dashboard from the deployment outputs.

### CloudWatch Alarms

An alarm is configured to alert when Lambda errors exceed 5 in a 5-minute period.

## Cost Considerations

This serverless architecture uses pay-per-use pricing:

- **Lambda**: Charged per invocation and duration
- **API Gateway**: Charged per request
- **DynamoDB**: Pay-per-request billing mode
- **S3**: Charged for storage and data transfer
- **CloudFront**: Charged for data transfer and requests
- **Bedrock**: Charged per input/output token

For cost optimization:
- Enable DynamoDB TTL for automatic cleanup (already configured)
- Use CloudFront caching for static assets
- Implement rate limiting to prevent abuse

## Security

- CORS is configured to allow cross-origin requests (customize for production)
- API Gateway throttling limits burst traffic
- Rate limiting prevents abuse from individual IPs
- CloudFront uses HTTPS only
- S3 bucket blocks public access; only CloudFront can access it

## Troubleshooting

### Common Issues

1. **"Access Denied" for Bedrock**
   - Ensure you've requested access to the Claude 3 model in the Bedrock console
   - Verify the Lambda function has the correct IAM permissions

2. **CORS Errors**
   - Check that the `API_ENDPOINT` in frontend matches your deployment
   - Verify CloudFront is properly routing `/api/*` paths to API Gateway

3. **Rate Limiting Not Working**
   - Ensure DynamoDB table exists and Lambda has permissions
   - Check CloudWatch logs for rate limiting errors

### Viewing Logs

```bash
# View Lambda logs
sam logs -n requirements-evaluator-dev --stack-name requirements-evaluator-dev --tail
```

## License

ISC

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run linting and tests
5. Submit a pull request
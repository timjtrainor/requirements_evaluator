# API Schema Documentation

This document describes the request and response schemas for the AI Requirements Quality Evaluator API.

## Base URL

The API is accessed via CloudFront or API Gateway:

- **CloudFront (recommended)**: `https://{cloudfront-domain}/evaluate`
- **API Gateway (direct)**: `https://{api-id}.execute-api.{region}.amazonaws.com/evaluate`

## Authentication

Currently, the API does not require authentication. Access is controlled via:
- Rate limiting (50 requests per IP per day by default)
- CORS restrictions (configurable)

## Endpoints

### POST /evaluate

Evaluates a software requirement for quality.

#### Request

**Method**: `POST`

**Headers**:
```
Content-Type: application/json
```

**Body Schema**:
```json
{
  "requirementText": string  // Required, 10-5000 characters
}
```

**Example Request**:
```json
{
  "requirementText": "The system shall allow users to log in using their email and password within 3 seconds."
}
```

**Validation Rules**:
- `requirementText` is required
- Must be a string
- Minimum length: 10 characters (configurable via `MIN_REQUIREMENT_LENGTH`)
- Maximum length: 5000 characters (configurable via `MAX_REQUIREMENT_LENGTH`)
- Cannot be empty or whitespace-only

#### Response

**Success Response** (200 OK):

**Schema**:
```json
{
  "ambiguity_detected": boolean,
  "ambiguity_details": string,
  "testable": boolean,
  "testability_details": string,
  "completeness_score": integer,  // 1-10
  "completeness_details": string,
  "issues": [string],
  "suggestions": [string]
}
```

**Field Descriptions**:

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `ambiguity_detected` | boolean | Whether vague, unclear, or subjective language was found | Required |
| `ambiguity_details` | string | Explanation of ambiguous terms or "None" if clear | Required |
| `testable` | boolean | Whether the requirement has measurable acceptance criteria | Required |
| `testability_details` | string | Explanation of testability assessment | Required |
| `completeness_score` | integer | How complete the requirement is | 1-10, required |
| `completeness_details` | string | Explanation of what information may be missing | Required |
| `issues` | array of strings | Specific problems identified in the requirement | Required, can be empty |
| `suggestions` | array of strings | Actionable improvement recommendations | Required, can be empty |

**Example Success Response**:
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

#### Error Responses

**400 Bad Request** - Invalid input

```json
{
  "error": "Request body is required"
}
```

Possible error messages:
- `"Request body is required"` - No body provided
- `"Invalid JSON in request body"` - Malformed JSON
- `"Missing required field: requirementText"` - Field not present
- `"requirementText must be a string"` - Wrong type
- `"requirementText cannot be empty"` - Empty or whitespace
- `"requirementText must be at least 10 characters"` - Too short
- `"requirementText exceeds maximum length of 5000 characters"` - Too long

**405 Method Not Allowed** - Wrong HTTP method

```json
{
  "error": "Method not allowed"
}
```

**429 Too Many Requests** - Rate limit exceeded

```json
{
  "error": "Daily rate limit of 50 requests exceeded. Please try again tomorrow."
}
```

**500 Internal Server Error** - Server-side error

```json
{
  "error": "AWS service error: {error_code}"
}
```

or

```json
{
  "error": "Internal server error"
}
```

## CORS Configuration

The API supports CORS with the following configuration:

- **Allowed Origins**: `*` (all origins)
- **Allowed Methods**: `POST`, `OPTIONS`
- **Allowed Headers**: `Content-Type`
- **Max Age**: 3600 seconds

## Rate Limiting

Rate limiting is enforced per source IP address:

- **Limit**: 50 requests per IP per day (configurable)
- **Reset**: Daily at midnight UTC
- **Behavior**: Returns 429 status code when exceeded
- **Bypass**: Set `SKIP_RATE_LIMIT=true` environment variable (not recommended for production)

## Examples

### cURL Example

```bash
curl -X POST https://your-cloudfront-domain/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "requirementText": "The system shall be user-friendly and fast."
  }'
```

### Python Example

```python
import requests
import json

url = "https://your-cloudfront-domain/evaluate"
payload = {
    "requirementText": "The system shall be user-friendly and fast."
}

response = requests.post(url, json=payload)
result = response.json()

print(f"Ambiguity Detected: {result['ambiguity_detected']}")
print(f"Testable: {result['testable']}")
print(f"Completeness Score: {result['completeness_score']}/10")
```

### JavaScript Example

```javascript
const evaluateRequirement = async (requirementText) => {
  const response = await fetch('https://your-cloudfront-domain/evaluate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ requirementText })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error);
  }

  return await response.json();
};

// Usage
evaluateRequirement('The system shall be user-friendly and fast.')
  .then(result => {
    console.log('Ambiguity:', result.ambiguity_detected);
    console.log('Testable:', result.testable);
    console.log('Score:', result.completeness_score);
  })
  .catch(error => console.error('Error:', error.message));
```

## Internal Processing

### Request Flow

1. API Gateway receives request
2. CloudFront forwards to Lambda (if using CloudFront)
3. Lambda validates request body
4. Lambda checks rate limit in DynamoDB
5. Lambda calls Amazon Bedrock with formatted prompt
6. Bedrock model generates evaluation
7. Lambda validates response schema using Pydantic
8. Lambda returns formatted response

### Timeout Behavior

- **Lambda Timeout**: 30 seconds (configurable via `lambda_timeout`)
- **Bedrock Timeout**: 30 seconds (configurable via `bedrock_timeout`)
- **API Gateway Timeout**: 30 seconds (hard limit)

If any timeout is exceeded, a 500 error is returned.

### Logging

All requests are logged with structured JSON including:
- Request ID
- Client IP
- Duration
- Model used
- Success/failure status
- Error details (if any)

Logs are available in CloudWatch under:
- `/aws/lambda/{function-name}`
- `/aws/apigateway/{project-name}-{environment}`

## Model-Specific Behavior

Different Bedrock models may have slight variations in response style:

### OpenAI Models
- More concise explanations
- Structured, bullet-point style issues
- Focus on technical completeness

### Claude Models
- More detailed explanations
- Narrative style with context
- Emphasis on clarity and user impact

All models are validated against the same schema to ensure consistency.

## Versioning

This is version 0.1.0 of the API. The API does not currently use URL-based versioning.

Future versions may introduce:
- API versioning in the URL path (`/v1/evaluate`, `/v2/evaluate`)
- Additional endpoints for batch evaluation
- Streaming responses for real-time feedback

## Support and Feedback

For issues or questions about the API:
1. Check the [README](README.md) for setup instructions
2. Review [SUPPORTED_MODELS.md](SUPPORTED_MODELS.md) for model-specific behavior
3. Check CloudWatch logs for detailed error information

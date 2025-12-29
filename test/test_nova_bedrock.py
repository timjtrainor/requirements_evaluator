import json
import boto3
import sys

def test_nova_bedrock():
    """
    Test script to verify Bedrock Nova Pro connection and signature.
    Run this with local AWS credentials.
    """
    model_id = "us.amazon.nova-pro-v1:0"
    region = "us-west-2"
    
    print(f"Testing Bedrock Nova Pro in {region}...")
    
    client = boto3.client(
        service_name="bedrock-runtime",
        region_name=region
    )
    
    prompt = "Hello, respond with 'Signature OK' if you receive this."
    
    request_body = {
        "schemaVersion": "messages-v1",
        "messages": [
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ],
        "inferenceConfig": {
            "maxTokens": 100,
            "temperature": 0.2
        }
    }
    
    try:
        response = client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body).encode("utf-8")
        )
        
        response_body = json.loads(response.get('body').read())
        content = response_body.get('output', {}).get('message', {}).get('content', [{}])[0].get('text', '')
        
        print("\nSuccess!")
        print(f"Response: {content}")
        
    except Exception as e:
        print("\nError occurred!")
        print(f"Type: {type(e).__name__}")
        print(f"Message: {str(e)}")
        
        if "IncompleteSignatureException" in str(e):
            print("\nSignature issue detected. This usually means the request body or headers don't match what the service expects.")

if __name__ == "__main__":
    test_nova_bedrock()

"""
Test cases for handler module.

Tests input validation, error handling, and integration with mocked Bedrock.
"""

import json
import os
import unittest
from unittest.mock import MagicMock, patch, Mock

# Set env vars before importing handler
os.environ["RATE_LIMIT_TABLE"] = "test-table"
os.environ["SKIP_RATE_LIMIT"] = "true"

from handler import validate_request, build_evaluation_prompt, get_client_ip, handler


class TestValidateRequest(unittest.TestCase):
    """Test cases for request validation."""
    
    def test_empty_body(self):
        """Test that empty body is rejected."""
        is_valid, error = validate_request({})
        self.assertFalse(is_valid)
        self.assertIn("empty", error.lower())
    
    def test_missing_requirement_text(self):
        """Test that missing requirementText is rejected."""
        is_valid, error = validate_request({"other_field": "value"})
        self.assertFalse(is_valid)
        self.assertIn("requirementText", error)
    
    def test_non_string_requirement_text(self):
        """Test that non-string requirementText is rejected."""
        is_valid, error = validate_request({"requirementText": 123})
        self.assertFalse(is_valid)
        self.assertIn("string", error)
    
    def test_empty_requirement_text(self):
        """Test that empty requirementText is rejected."""
        is_valid, error = validate_request({"requirementText": ""})
        self.assertFalse(is_valid)
        self.assertIn("empty", error.lower())
    
    def test_whitespace_only_requirement_text(self):
        """Test that whitespace-only requirementText is rejected."""
        is_valid, error = validate_request({"requirementText": "   "})
        self.assertFalse(is_valid)
        self.assertIn("empty", error.lower())
    
    def test_too_short_requirement_text(self):
        """Test that too short requirementText is rejected."""
        is_valid, error = validate_request({"requirementText": "short"})
        self.assertFalse(is_valid)
        self.assertIn("10", error)
    
    def test_too_long_requirement_text(self):
        """Test that too long requirementText is rejected."""
        long_text = "x" * 6000
        is_valid, error = validate_request({"requirementText": long_text})
        self.assertFalse(is_valid)
        self.assertIn("5000", error)
    
    def test_valid_requirement_text(self):
        """Test that valid requirementText passes validation."""
        is_valid, error = validate_request({
            "requirementText": "The system shall do something useful."
        })
        self.assertTrue(is_valid)
        self.assertEqual(error, "")


class TestBuildEvaluationPrompt(unittest.TestCase):
    """Test cases for prompt building."""
    
    def test_prompt_includes_requirement(self):
        """Test that prompt includes the requirement text."""
        requirement = "The system shall be fast."
        prompt = build_evaluation_prompt(requirement)
        self.assertIn(requirement, prompt)
    
    def test_prompt_includes_json_format(self):
        """Test that prompt specifies JSON format."""
        prompt = build_evaluation_prompt("test requirement")
        self.assertIn("JSON", prompt)
        self.assertIn("ambiguity_detected", prompt)
        self.assertIn("testable", prompt)
        self.assertIn("completeness_score", prompt)


class TestGetClientIp(unittest.TestCase):
    """Test cases for IP extraction."""
    
    def test_api_gateway_v1_format(self):
        """Test IP extraction from API Gateway v1 format."""
        event = {
            "requestContext": {
                "identity": {
                    "sourceIp": "1.2.3.4"
                }
            }
        }
        ip = get_client_ip(event)
        self.assertEqual(ip, "1.2.3.4")
    
    def test_x_forwarded_for_header(self):
        """Test IP extraction from X-Forwarded-For header."""
        event = {
            "requestContext": {},
            "headers": {
                "X-Forwarded-For": "1.2.3.4, 5.6.7.8"
            }
        }
        ip = get_client_ip(event)
        self.assertEqual(ip, "1.2.3.4")
    
    def test_lowercase_x_forwarded_for(self):
        """Test IP extraction from lowercase header."""
        event = {
            "requestContext": {},
            "headers": {
                "x-forwarded-for": "1.2.3.4"
            }
        }
        ip = get_client_ip(event)
        self.assertEqual(ip, "1.2.3.4")
    
    def test_unknown_ip(self):
        """Test that unknown is returned when no IP found."""
        event = {
            "requestContext": {},
            "headers": {}
        }
        ip = get_client_ip(event)
        self.assertEqual(ip, "unknown")


class TestHandler(unittest.TestCase):
    """Test cases for main Lambda handler."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_context = MagicMock()
        self.mock_context.request_id = "test-request-id"
    
    def test_options_request(self):
        """Test CORS preflight OPTIONS request."""
        event = {"httpMethod": "OPTIONS"}
        response = handler(event, self.mock_context)
        self.assertEqual(response["statusCode"], 200)
    
    def test_get_request_not_allowed(self):
        """Test that GET requests are rejected."""
        event = {"httpMethod": "GET"}
        response = handler(event, self.mock_context)
        self.assertEqual(response["statusCode"], 405)
        body = json.loads(response["body"])
        self.assertIn("error", body)
    
    def test_empty_body(self):
        """Test that empty body returns 400."""
        event = {
            "httpMethod": "POST",
            "body": ""
        }
        response = handler(event, self.mock_context)
        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertIn("error", body)
    
    def test_invalid_json_body(self):
        """Test that invalid JSON returns 400."""
        event = {
            "httpMethod": "POST",
            "body": "not json"
        }
        response = handler(event, self.mock_context)
        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertIn("JSON", body["error"])
    
    def test_invalid_requirement_text(self):
        """Test that invalid requirementText returns 400."""
        event = {
            "httpMethod": "POST",
            "body": json.dumps({"requirementText": "short"})
        }
        response = handler(event, self.mock_context)
        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertIn("error", body)
    
    @patch('handler.call_bedrock')
    def test_successful_evaluation(self, mock_bedrock):
        """Test successful evaluation flow."""
        # Mock Bedrock response
        mock_bedrock.return_value = {
            "ambiguity_detected": False,
            "ambiguity_details": "Clear requirement",
            "testable": True,
            "testability_details": "Has measurable criteria",
            "completeness_score": 8,
            "completeness_details": "Well defined",
            "issues": [],
            "suggestions": []
        }
        
        event = {
            "httpMethod": "POST",
            "body": json.dumps({
                "requirementText": "The system shall respond within 2 seconds."
            }),
            "requestContext": {
                "identity": {
                    "sourceIp": "1.2.3.4"
                }
            }
        }
        
        response = handler(event, self.mock_context)
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertIn("ambiguity_detected", body)
        self.assertIn("completeness_score", body)


if __name__ == "__main__":
    unittest.main()

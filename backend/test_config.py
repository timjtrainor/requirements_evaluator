"""
Unit tests for the config module.

Tests configuration loading, validation, and schema checking.
"""

import os
import unittest
from config import Config, validate_response_schema


class TestConfig(unittest.TestCase):
    """Test cases for Config class."""
    
    def test_default_model_id(self):
        """Test that default model ID is set correctly."""
        # Should default to openai.gpt-oss-120b-1:0 if no env var
        self.assertEqual(Config.get_model_id(), "openai.gpt-oss-120b-1:0")
    
    def test_default_region(self):
        """Test that default Bedrock region is us-east-1."""
        self.assertEqual(Config.get_bedrock_region(), "us-east-1")
    
    def test_default_rate_limit(self):
        """Test that default rate limit is 50."""
        self.assertEqual(Config.get_daily_rate_limit(), 50)
    
    def test_default_log_level(self):
        """Test that default log level is INFO."""
        self.assertEqual(Config.get_log_level(), "INFO")


class TestValidateResponseSchema(unittest.TestCase):
    """Test cases for response schema validation."""
    
    def test_valid_response(self):
        """Test that a valid response passes validation."""
        valid_response = {
            "ambiguity_detected": True,
            "ambiguity_details": "Some ambiguous terms found",
            "testable": False,
            "testability_details": "No measurable criteria",
            "completeness_score": 5,
            "completeness_details": "Missing several key elements",
            "issues": ["Vague terms", "No acceptance criteria"],
            "suggestions": ["Add specific metrics", "Define test cases"]
        }
        
        is_valid, error = validate_response_schema(valid_response)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_missing_required_field(self):
        """Test that missing required fields are detected."""
        invalid_response = {
            "ambiguity_detected": True,
            # Missing ambiguity_details
            "testable": False,
            "testability_details": "Details",
            "completeness_score": 5,
            "completeness_details": "Details",
            "issues": [],
            "suggestions": []
        }
        
        is_valid, error = validate_response_schema(invalid_response)
        self.assertFalse(is_valid)
        self.assertIn("ambiguity_details", error)
    
    def test_wrong_type_boolean(self):
        """Test that wrong type for boolean field is detected."""
        invalid_response = {
            "ambiguity_detected": "yes",  # Should be boolean
            "ambiguity_details": "Details",
            "testable": False,
            "testability_details": "Details",
            "completeness_score": 5,
            "completeness_details": "Details",
            "issues": [],
            "suggestions": []
        }
        
        is_valid, error = validate_response_schema(invalid_response)
        self.assertFalse(is_valid)
        self.assertIn("boolean", error)
    
    def test_wrong_type_integer(self):
        """Test that wrong type for integer field is detected."""
        invalid_response = {
            "ambiguity_detected": True,
            "ambiguity_details": "Details",
            "testable": False,
            "testability_details": "Details",
            "completeness_score": "5",  # Should be integer
            "completeness_details": "Details",
            "issues": [],
            "suggestions": []
        }
        
        is_valid, error = validate_response_schema(invalid_response)
        self.assertFalse(is_valid)
        self.assertIn("integer", error)
    
    def test_wrong_type_array(self):
        """Test that wrong type for array field is detected."""
        invalid_response = {
            "ambiguity_detected": True,
            "ambiguity_details": "Details",
            "testable": False,
            "testability_details": "Details",
            "completeness_score": 5,
            "completeness_details": "Details",
            "issues": "not an array",  # Should be array
            "suggestions": []
        }
        
        is_valid, error = validate_response_schema(invalid_response)
        self.assertFalse(is_valid)
        self.assertIn("array", error)
    
    def test_score_out_of_range_high(self):
        """Test that completeness score above 10 is rejected."""
        invalid_response = {
            "ambiguity_detected": True,
            "ambiguity_details": "Details",
            "testable": False,
            "testability_details": "Details",
            "completeness_score": 15,  # Out of range
            "completeness_details": "Details",
            "issues": [],
            "suggestions": []
        }
        
        is_valid, error = validate_response_schema(invalid_response)
        self.assertFalse(is_valid)
        self.assertIn("<=", error)
    
    def test_score_out_of_range_low(self):
        """Test that completeness score below 1 is rejected."""
        invalid_response = {
            "ambiguity_detected": True,
            "ambiguity_details": "Details",
            "testable": False,
            "testability_details": "Details",
            "completeness_score": 0,  # Out of range
            "completeness_details": "Details",
            "issues": [],
            "suggestions": []
        }
        
        is_valid, error = validate_response_schema(invalid_response)
        self.assertFalse(is_valid)
        self.assertIn(">=", error)
    
    def test_array_items_wrong_type(self):
        """Test that array items of wrong type are detected."""
        invalid_response = {
            "ambiguity_detected": True,
            "ambiguity_details": "Details",
            "testable": False,
            "testability_details": "Details",
            "completeness_score": 5,
            "completeness_details": "Details",
            "issues": [123, 456],  # Should be strings
            "suggestions": []
        }
        
        is_valid, error = validate_response_schema(invalid_response)
        self.assertFalse(is_valid)
        self.assertIn("string", error)
    
    def test_boundary_score_values(self):
        """Test that boundary score values (1 and 10) are accepted."""
        # Test score = 1
        response_1 = {
            "ambiguity_detected": True,
            "ambiguity_details": "Details",
            "testable": False,
            "testability_details": "Details",
            "completeness_score": 1,
            "completeness_details": "Details",
            "issues": [],
            "suggestions": []
        }
        
        is_valid, error = validate_response_schema(response_1)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Test score = 10
        response_10 = {
            "ambiguity_detected": True,
            "ambiguity_details": "Details",
            "testable": False,
            "testability_details": "Details",
            "completeness_score": 10,
            "completeness_details": "Details",
            "issues": [],
            "suggestions": []
        }
        
        is_valid, error = validate_response_schema(response_10)
        self.assertTrue(is_valid)
        self.assertIsNone(error)


if __name__ == "__main__":
    unittest.main()

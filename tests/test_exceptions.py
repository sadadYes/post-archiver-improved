"""
Tests for custom exception classes.

This module tests the custom exception hierarchy and error handling
functionality of the post archiver.
"""

import pytest
from unittest.mock import Mock

from post_archiver_improved.exceptions import (
    PostArchiverError, NetworkError, APIError, ParseError, JSONParseError,
    ValidationError, ConfigurationError, FileOperationError,
    RateLimitError, TimeoutError, ChannelNotFoundError,
    CommentExtractionError, ImageDownloadError
)


class TestPostArchiverError:
    """Test base PostArchiverError class."""
    
    def test_basic_error(self):
        """Test basic error creation."""
        error = PostArchiverError("Test error message")
        
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.error_code is None
        assert error.context == {}
        assert error.original_error is None
    
    def test_error_with_code(self):
        """Test error with error code."""
        error = PostArchiverError("Test error", error_code="TEST_001")
        
        assert error.error_code == "TEST_001"
        assert "TEST_001" in str(error)
    
    def test_error_with_context(self):
        """Test error with context information."""
        context = {"file": "test.json", "line": 42}
        error = PostArchiverError("Test error", context=context)
        
        assert error.context == context
    
    def test_error_with_original_error(self):
        """Test error wrapping another exception."""
        original = ValueError("Original error")
        error = PostArchiverError("Wrapper error", original_error=original)
        
        assert error.original_error == original
    
    def test_to_dict(self):
        """Test converting error to dictionary."""
        context = {"key": "value"}
        original = ValueError("Original")
        error = PostArchiverError(
            "Test error",
            error_code="TEST_001",
            context=context,
            original_error=original
        )
        
        error_dict = error.to_dict()
        
        assert error_dict["error_type"] == "PostArchiverError"
        assert error_dict["message"] == "Test error"
        assert error_dict["error_code"] == "TEST_001"
        assert error_dict["context"] == context
        assert "original_error" in error_dict


class TestNetworkError:
    """Test NetworkError class."""
    
    def test_basic_network_error(self):
        """Test basic network error."""
        error = NetworkError("Connection failed")
        
        assert isinstance(error, PostArchiverError)
        assert str(error) == "Connection failed"
    
    def test_network_error_with_status_code(self):
        """Test network error with HTTP status code."""
        error = NetworkError("HTTP error", status_code=404)
        
        assert error.status_code == 404
        assert error.context["status_code"] == 404
    
    def test_network_error_with_url(self):
        """Test network error with URL."""
        url = "https://example.com/api"
        error = NetworkError("Request failed", url=url)
        
        assert error.url == url
        assert error.context["url"] == url
    
    def test_network_error_full(self):
        """Test network error with all parameters."""
        error = NetworkError(
            "Request failed",
            status_code=500,
            url="https://example.com",
            error_code="NET_001"
        )
        
        assert error.status_code == 500
        assert error.url == "https://example.com"
        assert error.error_code == "NET_001"


class TestAPIError:
    """Test APIError class."""
    
    def test_basic_api_error(self):
        """Test basic API error."""
        error = APIError("API request failed")
        
        assert isinstance(error, PostArchiverError)
        assert str(error) == "API request failed"
    
    def test_api_error_with_response(self):
        """Test API error with response data."""
        response = {"error": "Invalid request", "code": 400}
        error = APIError("API error", api_response=response)
        
        assert error.context["api_response"] == response
    
    def test_api_error_with_endpoint(self):
        """Test API error with endpoint information."""
        endpoint = "/api/v1/posts"
        error = APIError("API error", endpoint=endpoint)
        
        assert error.context["endpoint"] == endpoint


class TestParseError:
    """Test ParseError class."""
    
    def test_basic_parse_error(self):
        """Test basic parse error."""
        error = ParseError("Failed to parse data")
        
        assert isinstance(error, PostArchiverError)
        assert str(error) == "Failed to parse data"
    
    def test_parse_error_with_source(self):
        """Test parse error with data source."""
        error = ParseError("Parse failed", data_source="API response")
        
        assert error.context["data_source"] == "API response"
    
    def test_parse_error_with_field_path(self):
        """Test parse error with field path."""
        error = ParseError("Missing field", field_path="data.posts[0].id")
        
        assert error.context["field_path"] == "data.posts[0].id"


class TestJSONParseError:
    """Test JSONParseError class."""
    
    def test_json_parse_error(self):
        """Test JSON parse error."""
        error = JSONParseError("Invalid JSON")
        
        assert isinstance(error, ParseError)
        assert isinstance(error, PostArchiverError)
    
    def test_json_parse_error_with_text(self):
        """Test JSON parse error with JSON text."""
        json_text = '{"invalid": json}'
        error = JSONParseError("Invalid JSON", json_text=json_text)
        
        assert error.context["json_preview"] == json_text  # Stored as json_preview, not json_text
        assert error.json_text == json_text  # Also available as direct attribute
    
    def test_json_parse_error_with_position(self):
        """Test JSON parse error with position."""
        error = JSONParseError("Invalid JSON", position=15)
        
        assert error.context["position"] == 15


class TestValidationError:
    """Test ValidationError class."""
    
    def test_basic_validation_error(self):
        """Test basic validation error."""
        error = ValidationError("Invalid input")
        
        assert isinstance(error, PostArchiverError)
        assert str(error) == "Invalid input"
    
    def test_validation_error_with_field(self):
        """Test validation error with field information."""
        error = ValidationError(
            "Invalid channel ID",
            field_name="channel_id",
            field_value="invalid_id",
            expected_format="UC followed by 22 characters"
        )
        
        assert error.context["field_name"] == "channel_id"
        assert error.context["field_value"] == "invalid_id"
        assert error.context["expected_format"] == "UC followed by 22 characters"


class TestConfigurationError:
    """Test ConfigurationError class."""
    
    def test_configuration_error(self):
        """Test configuration error."""
        error = ConfigurationError("Invalid configuration")
        
        assert isinstance(error, PostArchiverError)
    
    def test_configuration_error_with_file(self):
        """Test configuration error with file information."""
        error = ConfigurationError(
            "Invalid config",
            config_file="config.json",
            config_key="scraping.max_posts"
        )
        
        assert error.context["config_file"] == "config.json"
        assert error.context["config_key"] == "scraping.max_posts"


class TestFileOperationError:
    """Test FileOperationError class."""
    
    def test_file_operation_error(self):
        """Test file operation error."""
        error = FileOperationError("File operation failed")
        
        assert isinstance(error, PostArchiverError)
    
    def test_file_operation_error_with_details(self):
        """Test file operation error with details."""
        error = FileOperationError(
            "Write failed",
            file_path="/path/to/file.json",
            operation="write"
        )
        
        assert error.context["file_path"] == "/path/to/file.json"
        assert error.context["operation"] == "write"


class TestSpecializedErrors:
    """Test specialized error classes."""
    
    def test_rate_limit_error(self):
        """Test rate limit error."""
        error = RateLimitError("Rate limited", retry_after=300)
        
        assert isinstance(error, NetworkError)
        assert error.context["retry_after"] == 300
    
    def test_timeout_error(self):
        """Test timeout error."""
        error = TimeoutError("Request timed out", timeout_duration=30.0)
        
        assert isinstance(error, NetworkError)
        assert error.context["timeout_duration"] == 30.0
    
    def test_channel_not_found_error(self):
        """Test channel not found error."""
        error = ChannelNotFoundError("Channel not found", channel_id="UC123")
        
        assert isinstance(error, APIError)
        assert error.context["channel_id"] == "UC123"
    
    def test_comment_extraction_error(self):
        """Test comment extraction error."""
        error = CommentExtractionError(
            "Comment extraction failed",
            post_id="post123",
            comment_id="comment456"
        )
        
        assert isinstance(error, ParseError)
        assert error.context["post_id"] == "post123"
        assert error.context["comment_id"] == "comment456"
    
    def test_image_download_error(self):
        """Test image download error."""
        error = ImageDownloadError(
            "Download failed",
            image_url="https://example.com/image.jpg",
            image_size=1024000
        )
        
        assert isinstance(error, FileOperationError)
        assert error.context["image_url"] == "https://example.com/image.jpg"
        assert error.context["image_size"] == 1024000


class TestErrorInheritance:
    """Test error inheritance and polymorphism."""
    
    def test_error_inheritance(self):
        """Test that all errors inherit from PostArchiverError."""
        error_classes = [
            NetworkError, APIError, ParseError, JSONParseError,
            ValidationError, ConfigurationError, FileOperationError,
            RateLimitError, TimeoutError, ChannelNotFoundError,
            CommentExtractionError, ImageDownloadError
        ]
        
        for error_class in error_classes:
            error = error_class("Test message")
            assert isinstance(error, PostArchiverError)
            assert isinstance(error, Exception)
    
    def test_specialized_inheritance(self):
        """Test specialized error inheritance."""
        # Network errors
        assert issubclass(RateLimitError, NetworkError)
        assert issubclass(TimeoutError, NetworkError)
        
        # API errors
        assert issubclass(ChannelNotFoundError, APIError)
        
        # Parse errors
        assert issubclass(JSONParseError, ParseError)
        assert issubclass(CommentExtractionError, ParseError)
        
        # File operation errors
        assert issubclass(ImageDownloadError, FileOperationError)
    
    def test_error_catching(self):
        """Test that errors can be caught by base classes."""
        # Test catching specific error with base class
        try:
            raise NetworkError("Network error")
        except PostArchiverError as e:
            assert isinstance(e, NetworkError)
        
        # Test catching specialized error with intermediate class
        try:
            raise RateLimitError("Rate limited")
        except NetworkError as e:
            assert isinstance(e, RateLimitError)


class TestErrorContextManagement:
    """Test error context and metadata management."""
    
    def test_error_context_preservation(self):
        """Test that error context is preserved through inheritance."""
        original_context = {"key1": "value1"}
        error = NetworkError("Test", context=original_context, status_code=404)
        
        # Should preserve original context and add new context
        assert "key1" in error.context
        assert "status_code" in error.context
        assert error.context["key1"] == "value1"
        assert error.context["status_code"] == 404
    
    def test_error_serialization(self):
        """Test that errors can be properly serialized."""
        error = NetworkError(
            "Network error",
            status_code=500,
            url="https://example.com",
            error_code="NET_500"
        )
        
        error_dict = error.to_dict()
        
        # Verify all information is preserved
        assert error_dict["error_type"] == "NetworkError"
        assert error_dict["message"] == "Network error"
        assert error_dict["error_code"] == "NET_500"
        assert error_dict["context"]["status_code"] == 500
        assert error_dict["context"]["url"] == "https://example.com"


if __name__ == "__main__":
    pytest.main([__file__])

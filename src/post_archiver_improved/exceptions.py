"""
Custom exception classes for the post archiver.

This module defines specific exception types to provide better error handling
and debugging information throughout the application.
"""

import json
from typing import Optional, Dict, Any


class PostArchiverError(Exception):
    """
    Base exception class for post archiver errors.
    
    All custom exceptions in the post archiver inherit from this base class,
    providing a common interface and additional context.
    """
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        """
        Initialize the exception with additional context.
        
        Args:
            message: Human-readable error message
            error_code: Optional error code for programmatic handling
            context: Optional dictionary with additional context
            original_error: Optional original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.original_error = original_error
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for logging/serialization.
        
        Returns:
            Dictionary representation of the exception
        """
        result = {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "context": self.context
        }
        
        if self.original_error:
            result["original_error"] = {
                "type": self.original_error.__class__.__name__,
                "message": str(self.original_error)
            }
        
        return result
    
    def __str__(self) -> str:
        """Return string representation of the exception."""
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class NetworkError(PostArchiverError):
    """
    Raised when network operations fail.
    
    This includes HTTP errors, connection timeouts, DNS resolution failures,
    and other network-related issues.
    """
    
    def __init__(
        self, 
        message: str, 
        status_code: Optional[int] = None,
        url: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize network error with additional network context.
        
        Args:
            message: Error message
            status_code: HTTP status code if applicable
            url: URL that caused the error if applicable
            **kwargs: Additional arguments passed to parent
        """
        context = kwargs.pop('context', {})
        if status_code:
            context['status_code'] = status_code
        if url:
            context['url'] = url
        
        super().__init__(message, context=context, **kwargs)
        self.status_code = status_code
        self.url = url


class APIError(PostArchiverError):
    """
    Raised when YouTube API returns an error or unexpected response.
    
    This includes API rate limiting, authentication errors, invalid responses,
    and other API-specific issues.
    """
    
    def __init__(
        self, 
        message: str, 
        api_response: Optional[Dict[str, Any]] = None,
        endpoint: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize API error with additional API context.
        
        Args:
            message: Error message
            api_response: Raw API response if available
            endpoint: API endpoint that caused the error
            **kwargs: Additional arguments passed to parent
        """
        context = kwargs.pop('context', {})
        if endpoint:
            context['endpoint'] = endpoint
        if api_response:
            context['api_response'] = api_response
        
        super().__init__(message, context=context, **kwargs)
        self.api_response = api_response
        self.endpoint = endpoint


class ParseError(PostArchiverError):
    """
    Raised when parsing YouTube response data fails.
    
    This includes JSON parsing errors, missing required fields,
    unexpected data formats, and other data parsing issues.
    """
    
    def __init__(
        self, 
        message: str, 
        data_source: Optional[str] = None,
        field_path: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize parse error with additional parsing context.
        
        Args:
            message: Error message
            data_source: Source of the data being parsed
            field_path: JSON path where parsing failed
            **kwargs: Additional arguments passed to parent
        """
        context = kwargs.pop('context', {})
        if data_source:
            context['data_source'] = data_source
        if field_path:
            context['field_path'] = field_path
        
        super().__init__(message, context=context, **kwargs)
        self.data_source = data_source
        self.field_path = field_path


class JSONParseError(ParseError):
    """
    Raised when JSON parsing specifically fails.
    
    This is a specialized ParseError for JSON-related parsing issues.
    """
    
    def __init__(
        self, 
        message: str, 
        json_text: Optional[str] = None,
        position: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize JSON parse error with JSON context.
        
        Args:
            message: Error message
            json_text: Raw JSON text that failed to parse (truncated for logging)
            position: Character position where parsing failed
            **kwargs: Additional arguments passed to parent
        """
        context = kwargs.pop('context', {})
        if json_text:
            # Truncate JSON text for logging (first 200 chars)
            context['json_preview'] = json_text[:200] + ('...' if len(json_text) > 200 else '')
        if position:
            context['position'] = position
        
        super().__init__(message, data_source="JSON", context=context, **kwargs)
        self.json_text = json_text
        self.position = position


class ValidationError(PostArchiverError):
    """
    Raised when input validation fails.
    
    This includes invalid channel IDs, malformed URLs, invalid configuration
    values, and other input validation issues.
    """
    
    def __init__(
        self, 
        message: str, 
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        expected_format: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize validation error with validation context.
        
        Args:
            message: Error message
            field_name: Name of the field that failed validation
            field_value: Value that failed validation
            expected_format: Expected format description
            **kwargs: Additional arguments passed to parent
        """
        context = kwargs.pop('context', {})
        if field_name:
            context['field_name'] = field_name
        if field_value is not None:
            context['field_value'] = str(field_value)[:100]  # Truncate long values
        if expected_format:
            context['expected_format'] = expected_format
        
        super().__init__(message, context=context, **kwargs)
        self.field_name = field_name
        self.field_value = field_value
        self.expected_format = expected_format


class ConfigurationError(PostArchiverError):
    """
    Raised when configuration is invalid.
    
    This includes missing required configuration, invalid configuration values,
    and configuration file parsing errors.
    """
    
    def __init__(
        self, 
        message: str, 
        config_file: Optional[str] = None,
        config_key: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize configuration error with config context.
        
        Args:
            message: Error message
            config_file: Configuration file path if applicable
            config_key: Configuration key that caused the error
            **kwargs: Additional arguments passed to parent
        """
        context = kwargs.pop('context', {})
        if config_file:
            context['config_file'] = config_file
        if config_key:
            context['config_key'] = config_key
        
        super().__init__(message, context=context, **kwargs)
        self.config_file = config_file
        self.config_key = config_key


class FileOperationError(PostArchiverError):
    """
    Raised when file operations fail.
    
    This includes file read/write errors, permission issues, disk space issues,
    and other file system related problems.
    """
    
    def __init__(
        self, 
        message: str, 
        file_path: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize file operation error with file context.
        
        Args:
            message: Error message
            file_path: File path that caused the error
            operation: File operation that failed (read, write, delete, etc.)
            **kwargs: Additional arguments passed to parent
        """
        context = kwargs.get('context', {})
        if file_path:
            context['file_path'] = file_path
        if operation:
            context['operation'] = operation
        
        super().__init__(message, context=context, **kwargs)
        self.file_path = file_path
        self.operation = operation


class RateLimitError(NetworkError):
    """
    Raised when rate limiting is detected.
    
    This is a specialized NetworkError for rate limiting scenarios.
    """
    
    def __init__(
        self, 
        message: str, 
        retry_after: Optional[int] = None,
        limit_type: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize rate limit error with rate limiting context.
        
        Args:
            message: Error message
            retry_after: Suggested retry delay in seconds
            limit_type: Type of rate limit (e.g., 'api', 'request')
            **kwargs: Additional arguments passed to parent
        """
        context = kwargs.get('context', {})
        if retry_after:
            context['retry_after'] = retry_after
        if limit_type:
            context['limit_type'] = limit_type
        
        super().__init__(message, error_code="RATE_LIMIT", context=context, **kwargs)
        self.retry_after = retry_after
        self.limit_type = limit_type


class TimeoutError(NetworkError):
    """
    Raised when network requests timeout.
    
    This is a specialized NetworkError for timeout scenarios.
    """
    
    def __init__(
        self, 
        message: str, 
        timeout_duration: Optional[float] = None,
        **kwargs
    ):
        """
        Initialize timeout error with timeout context.
        
        Args:
            message: Error message
            timeout_duration: Timeout duration in seconds
            **kwargs: Additional arguments passed to parent
        """
        context = kwargs.get('context', {})
        if timeout_duration:
            context['timeout_duration'] = timeout_duration
        
        super().__init__(message, error_code="TIMEOUT", context=context, **kwargs)
        self.timeout_duration = timeout_duration


class ChannelNotFoundError(APIError):
    """
    Raised when a YouTube channel cannot be found.
    
    This is a specialized APIError for missing channel scenarios.
    """
    
    def __init__(
        self, 
        message: str, 
        channel_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize channel not found error with channel context.
        
        Args:
            message: Error message
            channel_id: Channel ID that was not found
            **kwargs: Additional arguments passed to parent
        """
        context = kwargs.get('context', {})
        if channel_id:
            context['channel_id'] = channel_id
        
        super().__init__(message, error_code="CHANNEL_NOT_FOUND", context=context, **kwargs)
        self.channel_id = channel_id


class CommentExtractionError(ParseError):
    """
    Raised when comment extraction fails.
    
    This is a specialized ParseError for comment-specific parsing issues.
    """
    
    def __init__(
        self, 
        message: str, 
        post_id: Optional[str] = None,
        comment_id: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize comment extraction error with comment context.
        
        Args:
            message: Error message
            post_id: Post ID where comment extraction failed
            comment_id: Specific comment ID if applicable
            **kwargs: Additional arguments passed to parent
        """
        context = kwargs.get('context', {})
        if post_id:
            context['post_id'] = post_id
        if comment_id:
            context['comment_id'] = comment_id
        
        super().__init__(message, data_source="comments", context=context, **kwargs)
        self.post_id = post_id
        self.comment_id = comment_id


class ImageDownloadError(FileOperationError):
    """
    Raised when image download operations fail.
    
    This is a specialized FileOperationError for image download scenarios.
    """
    
    def __init__(
        self, 
        message: str, 
        image_url: Optional[str] = None,
        image_size: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize image download error with image context.
        
        Args:
            message: Error message
            image_url: URL of the image that failed to download
            image_size: Expected image size if known
            **kwargs: Additional arguments passed to parent
        """
        context = kwargs.get('context', {})
        if image_url:
            context['image_url'] = image_url
        if image_size:
            context['image_size'] = image_size
        
        super().__init__(message, operation="download", context=context, **kwargs)
        self.image_url = image_url
        self.image_size = image_size

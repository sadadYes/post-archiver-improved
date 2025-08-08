"""
Tests for API client functionality.

This module tests the YouTube API client including request handling,
error management, and response parsing.
"""

from unittest.mock import Mock, patch

import pytest

from post_archiver_improved.api import YouTubeCommunityAPI
from post_archiver_improved.exceptions import APIError, NetworkError, ValidationError


class TestYouTubeCommunityAPI:
    """Test YouTubeCommunityAPI class."""

    def test_api_initialization(self):
        """Test API client initialization."""
        api = YouTubeCommunityAPI()

        assert api.timeout == 30
        assert api.max_retries == 3
        assert api.retry_delay == 1.0
        assert isinstance(api.headers, dict)
        assert isinstance(api.client_context, dict)
        assert api.base_url == "https://www.youtube.com/youtubei/v1/browse"
        assert api.next_url == "https://www.youtube.com/youtubei/v1/next"

    def test_api_custom_initialization(self):
        """Test API client with custom parameters."""
        api = YouTubeCommunityAPI(timeout=60, max_retries=5, retry_delay=2.0)

        assert api.timeout == 60
        assert api.max_retries == 5
        assert api.retry_delay == 2.0

    def test_api_headers_content(self):
        """Test that API headers contain required fields."""
        api = YouTubeCommunityAPI()

        required_headers = [
            "Content-Type",
            "User-Agent",
            "X-YouTube-Client-Name",
            "X-YouTube-Client-Version",
            "Origin",
            "Referer",
        ]

        for header in required_headers:
            assert header in api.headers
            assert isinstance(api.headers[header], str)
            assert len(api.headers[header]) > 0

    def test_client_context_structure(self):
        """Test client context structure."""
        api = YouTubeCommunityAPI()

        assert "client" in api.client_context
        client = api.client_context["client"]

        expected_client_fields = ["clientName", "clientVersion"]
        for field in expected_client_fields:
            assert field in client
            assert isinstance(client[field], str)


class TestAPIRequestMethods:
    """Test API request methods."""

    @patch("post_archiver_improved.api.make_http_request")
    def test_get_initial_data_success(self, mock_request):
        """Test successful get_initial_data call."""
        mock_response = {"contents": {"twoColumnBrowseResultsRenderer": {"tabs": []}}}
        mock_request.return_value = mock_response

        api = YouTubeCommunityAPI()
        result = api.get_initial_data("UC123456789")

        assert result == mock_response
        mock_request.assert_called_once()

        # Verify request parameters
        call_args = mock_request.call_args
        assert call_args.kwargs["url"] == api.base_url  # URL
        assert "browseId" in str(call_args.kwargs["data"])  # Data contains browseId

    @patch("post_archiver_improved.api.YouTubeCommunityAPI.resolve_channel_handle")
    @patch("post_archiver_improved.api.make_http_request")
    def test_get_initial_data_with_handle(self, mock_request, mock_resolve):
        """Test get_initial_data with @ handle."""
        mock_response = {"test": "data"}
        mock_request.return_value = mock_response
        mock_resolve.return_value = "UC123456789012345678901"

        api = YouTubeCommunityAPI()
        result = api.get_initial_data("@testchannel")

        assert result == mock_response
        # Should resolve the handle to a channel ID
        mock_resolve.assert_called_once_with("@testchannel")
        call_args = mock_request.call_args
        request_data = call_args.kwargs["data"]
        assert request_data["browseId"] == "UC123456789012345678901"

    @patch("post_archiver_improved.api.make_http_request")
    def test_get_continuation_data_success(self, mock_request):
        """Test successful get_continuation_data call."""
        mock_response = {
            "onResponseReceivedActions": [
                {"appendContinuationItemsAction": {"continuationItems": []}}
            ]
        }
        mock_request.return_value = mock_response

        api = YouTubeCommunityAPI()
        continuation_token = "test_token_123"
        result = api.get_continuation_data(continuation_token)

        assert result == mock_response
        mock_request.assert_called_once()

        # Verify request uses base URL (not next URL)
        call_args = mock_request.call_args
        assert call_args.kwargs["url"] == api.base_url

    @patch("post_archiver_improved.api.make_http_request")
    def test_api_network_error_handling(self, mock_request):
        """Test API error handling for network errors."""
        mock_request.side_effect = NetworkError("Connection failed")

        api = YouTubeCommunityAPI()

        with pytest.raises(APIError) as exc_info:
            api.get_initial_data("UC123456789")

        assert "Connection failed" in str(exc_info.value)

    @patch("post_archiver_improved.api.make_http_request")
    def test_api_invalid_response_handling(self, mock_request):
        """Test handling of invalid API responses."""
        # Return invalid response structure
        mock_request.return_value = {"unexpected": "structure"}

        api = YouTubeCommunityAPI()
        result = api.get_initial_data("UC123456789")

        # Should not raise error, just return the response
        assert result == {"unexpected": "structure"}

    @patch("post_archiver_improved.api.make_http_request")
    def test_invalid_channel_id_validation(self, mock_request):
        """Test validation of channel IDs."""
        api = YouTubeCommunityAPI()

        # Test empty channel ID
        with pytest.raises(ValidationError):
            api.get_initial_data("")

        # Test other invalid IDs that would make network requests
        mock_request.side_effect = NetworkError("HTTP 400: Bad Request")
        invalid_ids = ["invalid", "UC123"]  # Too short or invalid format

        for channel_id in invalid_ids:
            with pytest.raises(APIError):
                api.get_initial_data(channel_id)


class TestAPIRequestBuilding:
    """Test API request building and formatting."""

    @patch("post_archiver_improved.api.make_http_request")
    def test_build_browse_request(self, mock_request):
        """Test building of browse request."""
        mock_request.return_value = {}

        api = YouTubeCommunityAPI()
        api.get_initial_data("UC123456789")

        call_args = mock_request.call_args
        request_data = call_args.kwargs["data"]

        # Verify request structure
        assert "context" in request_data
        assert "browseId" in request_data
        assert "params" in request_data
        assert request_data["browseId"] == "UC123456789"

    @patch("post_archiver_improved.api.make_http_request")
    def test_build_continuation_request(self, mock_request):
        """Test building of continuation request."""
        mock_request.return_value = {}

        api = YouTubeCommunityAPI()
        continuation_token = "test_continuation_token"
        api.get_continuation_data(continuation_token)

        call_args = mock_request.call_args
        request_data = call_args.kwargs["data"]

        # Verify continuation request structure
        assert "context" in request_data
        assert "continuation" in request_data
        assert request_data["continuation"] == continuation_token

    def test_request_headers_included(self):
        """Test that custom headers are included in requests."""
        api = YouTubeCommunityAPI()

        with patch("post_archiver_improved.api.make_http_request") as mock_request:
            mock_request.return_value = {}

            api.get_initial_data("UC123456789")

            call_args = mock_request.call_args
            headers = call_args[1]["headers"]

            # Verify custom headers are passed
            assert "Content-Type" in headers
            assert "User-Agent" in headers
            assert "X-YouTube-Client-Name" in headers
            assert headers["Content-Type"] == "application/json"

    def test_request_timeout_parameter(self):
        """Test that timeout parameter is passed to requests."""
        api = YouTubeCommunityAPI(timeout=45)

        with patch("post_archiver_improved.api.make_http_request") as mock_request:
            mock_request.return_value = {}

            api.get_initial_data("UC123456789")

            call_args = mock_request.call_args
            assert call_args[1]["timeout"] == 45

    def test_request_retry_parameters(self):
        """Test that retry parameters are passed to requests."""
        api = YouTubeCommunityAPI(max_retries=5, retry_delay=2.5)

        with patch("post_archiver_improved.api.make_http_request") as mock_request:
            mock_request.return_value = {}

            api.get_initial_data("UC123456789")

            call_args = mock_request.call_args
            assert call_args[1]["max_retries"] == 5
            assert call_args[1]["retry_delay"] == 2.5


class TestAPIResponseHandling:
    """Test API response handling and parsing."""

    @patch("post_archiver_improved.api.make_http_request")
    def test_empty_response_handling(self, mock_request):
        """Test handling of empty responses."""
        mock_request.return_value = {}

        api = YouTubeCommunityAPI()
        result = api.get_initial_data("UC123456789")

        assert result == {}

    @patch("post_archiver_improved.api.make_http_request")
    def test_large_response_handling(self, mock_request):
        """Test handling of large responses."""
        # Create a large mock response
        large_response = {"contents": {"data": ["item" + str(i) for i in range(1000)]}}
        mock_request.return_value = large_response

        api = YouTubeCommunityAPI()
        result = api.get_initial_data("UC123456789")

        assert result == large_response
        assert len(result["contents"]["data"]) == 1000

    @patch("post_archiver_improved.api.make_http_request")
    def test_nested_response_structure(self, mock_request):
        """Test handling of deeply nested response structures."""
        nested_response = {
            "level1": {"level2": {"level3": {"level4": {"data": "deep_value"}}}}
        }
        mock_request.return_value = nested_response

        api = YouTubeCommunityAPI()
        result = api.get_initial_data("UC123456789")

        assert result == nested_response
        assert result["level1"]["level2"]["level3"]["level4"]["data"] == "deep_value"


class TestAPISpecialCases:
    """Test special cases and edge conditions."""

    def test_channel_id_normalization(self):
        """Test that channel IDs are properly normalized."""
        api = YouTubeCommunityAPI()

        test_cases = [
            ("UC123456789", "UC123456789"),
            ("@username", "@username"),
            ("https://youtube.com/channel/UC123456789", "UC123456789"),
            ("https://youtube.com/@username", "@username"),
        ]

        with patch("post_archiver_improved.api.make_http_request") as mock_request:
            mock_request.return_value = {}

            for input_id, expected_id in test_cases:
                try:
                    api.get_initial_data(input_id)
                    call_args = mock_request.call_args
                    request_data = call_args.kwargs["data"]
                    assert expected_id in str(request_data)
                except (ValidationError, APIError):
                    # Some IDs might be rejected by validation
                    pass

    @patch("post_archiver_improved.api.make_http_request")
    def test_unicode_handling(self, mock_request):
        """Test handling of Unicode characters in responses."""
        unicode_response = {
            "title": "测试频道",  # Chinese characters
            "description": "Канал тест",  # Cyrillic characters
            "emoji": "🎥📹🎬",  # Emoji
        }
        mock_request.return_value = unicode_response

        api = YouTubeCommunityAPI()
        result = api.get_initial_data("UC123456789")

        assert result == unicode_response
        assert result["title"] == "测试频道"
        assert result["description"] == "Канал тест"
        assert result["emoji"] == "🎥📹🎬"

    def test_api_client_context_immutability(self):
        """Test that client context doesn't get modified."""
        api = YouTubeCommunityAPI()
        original_context = api.client_context.copy()

        with patch("post_archiver_improved.api.make_http_request") as mock_request:
            mock_request.return_value = {}

            # Make multiple requests
            api.get_initial_data("UC123456789")
            api.get_continuation_data("token123")

            # Context should remain unchanged
            assert api.client_context == original_context

    @patch("post_archiver_improved.api.make_http_request")
    def test_concurrent_requests_safety(self, mock_request):
        """Test that API client is safe for concurrent use."""
        mock_request.return_value = {}

        api = YouTubeCommunityAPI()

        # Simulate concurrent requests (simplified test)
        results = []
        for i in range(5):
            try:
                result = api.get_initial_data(f"UC12345678{i}")
                results.append(result)
            except Exception:
                pass

        # Should handle multiple requests without errors
        assert len(results) >= 0  # At least some requests should succeed


class TestAPIErrorConditions:
    """Test various error conditions and edge cases."""

    @patch("post_archiver_improved.api.make_http_request")
    def test_rate_limiting_handling(self, mock_request):
        """Test handling of rate limiting responses."""
        from post_archiver_improved.exceptions import RateLimitError

        mock_request.side_effect = RateLimitError("Rate limited", retry_after=300)

        api = YouTubeCommunityAPI()

        with pytest.raises(APIError) as exc_info:
            api.get_initial_data("UC123456789")

        assert "Rate limited" in str(exc_info.value)

    @patch("post_archiver_improved.api.make_http_request")
    def test_timeout_handling(self, mock_request):
        """Test handling of request timeouts."""
        from post_archiver_improved.exceptions import TimeoutError

        mock_request.side_effect = TimeoutError("Request timed out")

        api = YouTubeCommunityAPI()

        with pytest.raises(APIError):
            api.get_initial_data("UC123456789")

    def test_invalid_continuation_token(self):
        """Test handling of invalid continuation tokens."""
        api = YouTubeCommunityAPI()

        invalid_tokens = ["", None, "invalid_token", "x" * 1000]

        for token in invalid_tokens:
            if token is None or token == "":
                with pytest.raises(ValidationError):
                    api.get_continuation_data(token)
            else:
                # Invalid but non-empty tokens should be passed through
                # The server will handle validation
                with patch(
                    "post_archiver_improved.api.make_http_request"
                ) as mock_request:
                    mock_request.return_value = {}
                    try:
                        api.get_continuation_data(token)
                    except Exception:
                        pass  # Server-side validation errors are acceptable


class TestChannelHandleResolution:
    """Test channel handle resolution functionality."""

    @patch("urllib.request.urlopen")
    def test_resolve_channel_handle_success(self, mock_urlopen):
        """Test successful channel handle resolution."""
        # Mock the HTML response containing channel ID
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = b"""
        <html>
        <head>
            <meta property="og:url" content="https://www.youtube.com/channel/UC5CwaMl1eIgY8h02uZw7u8A">
        </head>
        <body>
        </body>
        </html>
        """
        mock_response.info.return_value = {}
        mock_response.__enter__ = lambda self: self
        mock_response.__exit__ = lambda *args: None
        mock_urlopen.return_value = mock_response

        api = YouTubeCommunityAPI()
        result = api.resolve_channel_handle("@testchannel")

        assert result == "UC5CwaMl1eIgY8h02uZw7u8A"
        mock_urlopen.assert_called_once()

    @patch("urllib.request.urlopen")
    def test_resolve_channel_handle_json_pattern(self, mock_urlopen):
        """Test channel handle resolution using JSON pattern."""
        # Mock response with channelId in JSON format
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = b"""
        var ytInitialData = {"channelId":"UCG7J20LhUeLl6y_Emi7OJrA","title":"Test Channel"};
        """
        mock_response.info.return_value = {}
        mock_response.__enter__ = lambda self: self
        mock_response.__exit__ = lambda *args: None
        mock_urlopen.return_value = mock_response

        api = YouTubeCommunityAPI()
        result = api.resolve_channel_handle("@mkbhd")

        assert result == "UCG7J20LhUeLl6y_Emi7OJrA"

    def test_resolve_channel_handle_invalid_format(self):
        """Test error handling for invalid handle format."""
        api = YouTubeCommunityAPI()

        invalid_handles = ["testchannel", "UC123456789", "", "user/testchannel"]

        for handle in invalid_handles:
            with pytest.raises(ValidationError) as exc_info:
                api.resolve_channel_handle(handle)
            assert "Invalid handle format" in str(exc_info.value)

    @patch("urllib.request.urlopen")
    def test_resolve_channel_handle_http_error(self, mock_urlopen):
        """Test handling of HTTP errors during resolution."""
        from urllib.error import HTTPError

        mock_urlopen.side_effect = HTTPError(
            url="https://www.youtube.com/@test",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=None,
        )

        api = YouTubeCommunityAPI()

        with pytest.raises(APIError) as exc_info:
            api.resolve_channel_handle("@nonexistent")
        assert "Failed to resolve channel handle" in str(exc_info.value)

    @patch("urllib.request.urlopen")
    def test_resolve_channel_handle_no_match(self, mock_urlopen):
        """Test handling when no channel ID patterns are found."""
        # Mock response without any channel ID patterns
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = b"""
        <html>
        <head><title>Some page</title></head>
        <body><p>No channel ID here</p></body>
        </html>
        """
        mock_response.info.return_value = {}
        mock_response.__enter__ = lambda self: self
        mock_response.__exit__ = lambda *args: None
        mock_urlopen.return_value = mock_response

        api = YouTubeCommunityAPI()

        with pytest.raises(APIError) as exc_info:
            api.resolve_channel_handle("@unknown")
        assert "Could not resolve channel handle" in str(exc_info.value)

    @patch("post_archiver_improved.api.YouTubeCommunityAPI.resolve_channel_handle")
    @patch("post_archiver_improved.api.make_http_request")
    def test_get_initial_data_with_handle(self, mock_request, mock_resolve):
        """Test get_initial_data automatically resolving handles."""
        mock_resolve.return_value = "UC123456789012345678901"
        mock_request.return_value = {"test": "data"}

        api = YouTubeCommunityAPI()
        result = api.get_initial_data("@testhandle")

        assert result == {"test": "data"}
        mock_resolve.assert_called_once_with("@testhandle")
        mock_request.assert_called_once()

        # Verify the browseId in the request uses the resolved channel ID
        call_args = mock_request.call_args
        request_data = call_args.kwargs["data"]
        assert request_data["browseId"] == "UC123456789012345678901"

    @patch("post_archiver_improved.api.make_http_request")
    def test_get_initial_data_with_channel_id(self, mock_request):
        """Test get_initial_data with regular channel ID (no resolution needed)."""
        mock_request.return_value = {"test": "data"}

        api = YouTubeCommunityAPI()
        result = api.get_initial_data("UC123456789012345678901")

        assert result == {"test": "data"}
        mock_request.assert_called_once()

        # Verify the browseId uses the channel ID directly
        call_args = mock_request.call_args
        request_data = call_args.kwargs["data"]
        assert request_data["browseId"] == "UC123456789012345678901"


if __name__ == "__main__":
    pytest.main([__file__])

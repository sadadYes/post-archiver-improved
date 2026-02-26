"""
Tests for utility functions.

This module tests HTTP requests, file operations, validation functions, and other utility functionality.
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

import pytest

from post_archiver_improved.exceptions import (
    NetworkError,
    RateLimitError,
)
from post_archiver_improved.utils import (
    create_backup_filename,
    download_image,
    format_file_size,
    load_cookies_from_netscape_file,
    make_http_request,
    sanitize_filename,
    validate_channel_id,
)


class TestMakeHttpRequest:
    """Test make_http_request function."""

    @patch("post_archiver_improved.utils.urlopen")
    def test_successful_get_request(self, mock_urlopen):
        """Test successful GET request."""
        # Mock response
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({"key": "value"}).encode("utf-8")
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = make_http_request("https://example.com/api")

        assert result == {"key": "value"}
        mock_urlopen.assert_called_once()

    @patch("post_archiver_improved.utils.urlopen")
    def test_successful_post_request(self, mock_urlopen):
        """Test successful POST request."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({"success": True}).encode("utf-8")
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        data = {"test": "data"}
        result = make_http_request("https://example.com/api", data=data, method="POST")

        assert result == {"success": True}
        mock_urlopen.assert_called_once()

        # Check that request was made with correct data
        call_args = mock_urlopen.call_args[0][0]
        assert call_args.data is not None

    @patch("post_archiver_improved.utils.urlopen")
    def test_request_with_headers(self, mock_urlopen):
        """Test request with custom headers."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({}).encode("utf-8")
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        headers = {"Authorization": "Bearer token"}
        make_http_request("https://example.com/api", headers=headers)

        # Check that headers were added to request
        call_args = mock_urlopen.call_args[0][0]
        assert call_args.get_header("Authorization") == "Bearer token"

    @patch("post_archiver_improved.utils.urlopen")
    def test_http_error_handling(self, mock_urlopen):
        """Test HTTP error handling."""
        mock_urlopen.side_effect = HTTPError(
            "https://example.com", 404, "Not Found", {}, None
        )

        with pytest.raises(NetworkError) as exc_info:
            make_http_request("https://example.com/api")

        assert "404" in str(exc_info.value)
        assert "Not Found" in str(exc_info.value)

    @patch("post_archiver_improved.utils.urlopen")
    def test_url_error_handling(self, mock_urlopen):
        """Test URL error handling."""
        mock_urlopen.side_effect = URLError("Connection failed")

        with pytest.raises(NetworkError):
            make_http_request("https://example.com/api")

    @patch("post_archiver_improved.utils.urlopen")
    def test_rate_limit_detection(self, mock_urlopen):
        """Test rate limit detection."""
        mock_urlopen.side_effect = HTTPError(
            "https://example.com", 429, "Too Many Requests", {}, None
        )

        with pytest.raises(RateLimitError) as exc_info:
            make_http_request("https://example.com/api")

        assert "429" in str(exc_info.value)

    @patch("post_archiver_improved.utils.urlopen")
    @patch("post_archiver_improved.utils.time.sleep")
    def test_retry_logic(self, mock_sleep, mock_urlopen):
        """Test retry logic with exponential backoff."""
        # Test that retry logic is triggered by checking call count
        mock_urlopen.side_effect = [
            URLError("Connection failed"),
            URLError("Connection failed"),
            URLError("Connection failed"),
            URLError("Connection failed"),  # Will fail after max retries
        ]

        with pytest.raises(NetworkError):
            make_http_request("https://example.com/api", max_retries=3)

        # Should try 4 times total (initial + 3 retries)
        assert mock_urlopen.call_count == 4
        # Should sleep 3 times (between retries)
        assert mock_sleep.call_count == 3

    @patch("post_archiver_improved.utils.urlopen")
    def test_max_retries_exceeded(self, mock_urlopen):
        """Test behavior when max retries are exceeded."""
        mock_urlopen.side_effect = URLError("Connection failed")

        with pytest.raises(NetworkError):
            make_http_request("https://example.com/api", max_retries=2)

        assert mock_urlopen.call_count == 3  # Initial + 2 retries

    @patch("post_archiver_improved.utils.urlopen")
    def test_invalid_json_response(self, mock_urlopen):
        """Test handling of invalid JSON response."""
        mock_response = Mock()
        mock_response.read.return_value = b"invalid json response"
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with pytest.raises(NetworkError):
            make_http_request("https://example.com/api")

    def test_request_timeout(self):
        """Test request timeout parameter."""
        # This test verifies that timeout is passed to the request
        with patch("post_archiver_improved.utils.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = json.dumps({}).encode("utf-8")
            mock_response.status = 200
            mock_urlopen.return_value.__enter__.return_value = mock_response

            make_http_request("https://example.com/api", timeout=10)

            # Check that timeout was passed to urlopen
            call_args = mock_urlopen.call_args
            assert call_args[1]["timeout"] == 10

            # Verify timeout was passed
            call_args = mock_urlopen.call_args
            assert call_args[1]["timeout"] == 10


class TestValidateChannelId:
    """Test validate_channel_id function."""

    def test_valid_channel_ids(self):
        """Test validation of valid channel IDs."""
        valid_ids = [
            "UC1234567890123456789012",  # Standard format
            "@username",  # Handle format
            "c/channelname",  # Custom URL format
            "channel/UC1234567890123456789012",  # Channel path format
        ]

        for channel_id in valid_ids:
            assert validate_channel_id(channel_id), f"Should be valid: {channel_id}"

    def test_invalid_channel_ids(self):
        """Test validation of invalid channel IDs."""
        invalid_ids = [
            "",  # Empty string
            "UC123",  # Too short
            "invalid",  # Invalid format
            "https://google.com",  # Wrong domain
            "@",  # Handle without name
            "UC" + "x" * 50,  # Too long
        ]

        for channel_id in invalid_ids:
            assert not validate_channel_id(channel_id), (
                f"Should be invalid: {channel_id}"
            )

    def test_channel_id_edge_cases(self):
        """Test edge cases for channel ID validation."""
        # Minimum valid UC ID length
        assert validate_channel_id("UC" + "1" * 22)

        # Correct length (24 characters total including UC)
        assert validate_channel_id("UC" + "1" * 22)

        # Handle with special characters
        assert validate_channel_id("@user_name-123")

        # Case sensitivity should fail for lowercase UC
        assert not validate_channel_id("uc1234567890123456789012")


class TestSanitizeFilename:
    """Test sanitize_filename function."""

    def test_basic_sanitization(self):
        """Test basic filename sanitization."""
        assert sanitize_filename("normal_filename.txt") == "normal_filename.txt"
        assert sanitize_filename("file with spaces.txt") == "file_with_spaces.txt"

    def test_remove_invalid_characters(self):
        """Test removal of invalid characters."""
        test_cases = [
            ("file/with/slashes.txt", "file_with_slashes.txt"),
            ("file\\with\\backslashes.txt", "file_with_backslashes.txt"),
            ("file:with:colons.txt", "file_with_colons.txt"),
            ("file*with*asterisks.txt", "file_with_asterisks.txt"),
            ("file?with?questions.txt", "file_with_questions.txt"),
            ('file"with"quotes.txt', "file_with_quotes.txt"),
            ("file<with>brackets.txt", "file_with_brackets.txt"),
            ("file|with|pipes.txt", "file_with_pipes.txt"),
        ]

        for input_name, expected in test_cases:
            assert sanitize_filename(input_name) == expected

    def test_length_limiting(self):
        """Test filename length limiting."""
        long_name = "a" * 300 + ".txt"
        sanitized = sanitize_filename(long_name)

        assert len(sanitized) <= 255  # Common filesystem limit
        assert sanitized.endswith(".txt")  # Extension preserved

    def test_preserve_extensions(self):
        """Test that file extensions are preserved."""
        test_cases = [
            ("file.jpg", ".jpg"),
            ("file.with.multiple.dots.json", ".json"),
            ("file", ""),  # No extension
            (".hidden", ""),  # Hidden file without extension
        ]

        for filename, expected_ext in test_cases:
            sanitized = sanitize_filename(filename)
            if expected_ext:
                assert sanitized.endswith(expected_ext)

    def test_empty_and_special_names(self):
        """Test empty and special filename cases."""
        assert sanitize_filename("") == "untitled"
        assert sanitize_filename("...") == "untitled"
        assert sanitize_filename("   ") == "untitled"
        assert sanitize_filename('/\\:*?"<>|') == "untitled"


class TestFormatFileSize:
    """Test format_file_size function."""

    def test_byte_formatting(self):
        """Test formatting of file sizes in bytes."""
        test_cases = [(0, "0 B"), (1, "1.0 B"), (512, "512.0 B"), (1023, "1023.0 B")]

        for size, expected in test_cases:
            assert format_file_size(size) == expected

    def test_kilobyte_formatting(self):
        """Test formatting of file sizes in kilobytes."""
        test_cases = [
            (1024, "1.0 KB"),
            (1536, "1.5 KB"),
            (2048, "2.0 KB"),
            (1048575, "1024.0 KB"),  # Just under 1 MB
        ]

        for size, expected in test_cases:
            assert format_file_size(size) == expected

    def test_megabyte_formatting(self):
        """Test formatting of file sizes in megabytes."""
        test_cases = [
            (1048576, "1.0 MB"),  # 1 MB
            (1572864, "1.5 MB"),  # 1.5 MB
            (2097152, "2.0 MB"),  # 2 MB
            (1073741823, "1024.0 MB"),  # Just under 1 GB
        ]

        for size, expected in test_cases:
            assert format_file_size(size) == expected

    def test_gigabyte_formatting(self):
        """Test formatting of file sizes in gigabytes."""
        test_cases = [
            (1073741824, "1.0 GB"),  # 1 GB
            (1610612736, "1.5 GB"),  # 1.5 GB
            (2147483648, "2.0 GB"),  # 2 GB
        ]

        for size, expected in test_cases:
            assert format_file_size(size) == expected

    def test_negative_sizes(self):
        """Test handling of negative file sizes."""
        assert format_file_size(-1) == "-1.0 B"
        assert (
            format_file_size(-1024) == "-1024.0 B"
        )  # Negative numbers don't get converted


class TestCreateBackupFilename:
    """Test create_backup_filename function."""

    def test_basic_backup_naming(self, temp_dir):
        """Test basic backup filename creation."""
        original_file = temp_dir / "test.json"
        original_file.write_text("{}")

        backup_name = create_backup_filename(original_file)

        assert backup_name.parent == original_file.parent
        assert backup_name.stem.startswith("test")
        assert backup_name.suffix == ".json"
        assert "backup" in backup_name.name

    def test_backup_with_timestamp(self, temp_dir):
        """Test that backup includes timestamp."""
        original_file = temp_dir / "data.txt"
        original_file.write_text("content")

        backup_name = create_backup_filename(original_file)

        # Should contain timestamp-like pattern
        import re

        timestamp_pattern = r"\d{8}_\d{6}"  # YYYYMMDD_HHMMSS
        assert re.search(timestamp_pattern, backup_name.name)

    def test_backup_nonexistent_file(self, temp_dir):
        """Test backup naming for non-existent file."""
        original_file = temp_dir / "nonexistent.json"

        backup_name = create_backup_filename(original_file)

        assert backup_name.parent == original_file.parent
        assert "backup" in backup_name.name
        assert backup_name.suffix == ".json"

    @patch("post_archiver_improved.utils.datetime")
    def test_multiple_backups_different_names(self, mock_datetime, temp_dir):
        """Test that multiple backups get different names."""
        original_file = temp_dir / "test.json"
        original_file.write_text("{}")

        mock_datetime.now.side_effect = [
            Mock(strftime=Mock(return_value="20240101_120000")),
            Mock(strftime=Mock(return_value="20240101_120001")),
        ]

        backup1 = create_backup_filename(original_file)
        backup2 = create_backup_filename(original_file)

        assert backup1 != backup2


class TestDownloadImage:
    """Test download_image function."""

    @patch("post_archiver_improved.utils.urlopen")
    def test_successful_image_download(self, mock_urlopen, temp_dir):
        """Test successful image download."""
        # Mock response with proper file-like read behavior for shutil.copyfileobj
        mock_response = Mock()
        mock_response.status = 200
        mock_response.headers = {"content-type": "image/jpeg"}
        # side_effect returns data on first call, then empty bytes to signal EOF
        mock_response.read.side_effect = [b"fake_image_data", b""]
        mock_urlopen.return_value.__enter__.return_value = mock_response

        image_url = "https://example.com/image.jpg"
        output_dir = temp_dir

        result = download_image(image_url, "test_image", output_dir)

        assert result is not None
        result_path = Path(result)
        assert result_path.exists()
        assert result_path.read_bytes() == b"fake_image_data"
        mock_urlopen.assert_called_once()

    @patch("post_archiver_improved.utils.urlopen")
    def test_download_creates_directory(self, mock_urlopen, temp_dir):
        """Test that download creates output directory."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.read.side_effect = [b"image_data", b""]
        mock_urlopen.return_value.__enter__.return_value = mock_response

        image_url = "https://example.com/image.jpg"
        output_dir = temp_dir / "nested"

        result = download_image(image_url, "test_image", output_dir)

        images_dir = output_dir / "images"
        assert images_dir.exists()
        assert result is not None
        result_path = Path(result)
        assert result_path.parent == images_dir

    @patch("post_archiver_improved.utils.urlopen")
    def test_download_with_custom_filename(self, mock_urlopen, temp_dir):
        """Test download with custom filename."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.read.side_effect = [b"image_data", b""]
        mock_urlopen.return_value.__enter__.return_value = mock_response

        image_url = "https://example.com/image.jpg"
        output_dir = temp_dir
        custom_filename = "custom_name.jpg"

        result = download_image(image_url, custom_filename, output_dir)

        assert result is not None
        result_path = Path(result)
        assert result_path.name == custom_filename

    @patch("post_archiver_improved.utils.urlopen")
    def test_download_network_error(self, mock_urlopen, temp_dir):
        """Test download network error handling."""
        mock_urlopen.side_effect = HTTPError(
            "https://example.com", 404, "Not Found", {}, None
        )

        image_url = "https://example.com/image.jpg"
        output_dir = temp_dir

        result = download_image(image_url, "test_image", output_dir)

        # Should return None on failure, not raise exception
        assert result is None

    @patch("post_archiver_improved.utils.urlopen")
    def test_download_invalid_url(self, mock_urlopen, temp_dir):
        """Test download with invalid URL."""
        mock_urlopen.side_effect = URLError("unknown url type: 'not_a_url'")

        image_url = "not_a_url"
        output_dir = temp_dir

        result = download_image(image_url, "test_image", output_dir)

        # Should return None on failure, not raise exception
        assert result is None

    def test_download_permission_error(self, temp_dir):
        """Test download with permission error."""
        # Create read-only directory
        readonly_dir = temp_dir / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)

        try:
            image_url = "https://example.com/image.jpg"

            result = download_image(image_url, "test_image", readonly_dir)

            # Should return None on failure, not raise exception
            assert result is None

        finally:
            # Restore permissions for cleanup
            readonly_dir.chmod(0o755)


class TestUtilityIntegration:
    """Test integration between utility functions."""

    def test_channel_id_and_sanitization(self):
        """Test interaction between channel ID validation and filename sanitization."""
        # Valid channel ID format
        channel_id = "UC1234567890123456789012"

        # Should be valid as channel ID
        is_valid = validate_channel_id(channel_id)
        assert is_valid

        # Should be sanitized for filename use
        test_filename = "test*file<name>.json"
        sanitized = sanitize_filename(test_filename)
        assert "/" not in sanitized
        assert ":" not in sanitized
        assert "*" not in sanitized
        assert "<" not in sanitized

    def test_file_operations_with_backup(self, temp_dir):
        """Test file operations with backup creation."""
        original_file = temp_dir / "test.json"
        original_file.write_text('{"original": "data"}')

        # Create backup
        backup_file = create_backup_filename(original_file)

        # Simulate backup creation
        backup_file.write_text(original_file.read_text())

        # Verify both files exist and have same content
        assert original_file.exists()
        assert backup_file.exists()
        assert original_file.read_text() == backup_file.read_text()

        # Verify backup has different name
        assert original_file.name != backup_file.name
        assert "backup" in backup_file.name


class TestLoadCookiesFromNetscapeFile:
    """Test load_cookies_from_netscape_file function."""

    def test_load_valid_cookies(self, temp_dir):
        """Test loading valid Netscape format cookies."""
        cookies_file = temp_dir / "cookies.txt"

        # Create a sample Netscape format cookie file
        cookie_content = """# Netscape HTTP Cookie File
# This is a generated file!  Do not edit.

.youtube.com\tTRUE\t/\tFALSE\t1735689600\tSIDCC\tAA1234567890
.youtube.com\tTRUE\t/\tTRUE\t1735689600\t__Secure-1PSIDCC\tBB1234567890
.google.com\tTRUE\t/\tFALSE\t1735689600\tNID\tCC1234567890
example.com\tTRUE\t/\tFALSE\t1735689600\tother_cookie\tignored
"""
        cookies_file.write_text(cookie_content)

        cookies = load_cookies_from_netscape_file(cookies_file)

        assert cookies is not None
        assert len(cookies) == 3
        assert cookies["SIDCC"] == "AA1234567890"
        assert cookies["__Secure-1PSIDCC"] == "BB1234567890"
        assert cookies["NID"] == "CC1234567890"
        assert "other_cookie" not in cookies  # Should ignore non-YouTube/Google cookies

    def test_load_cookies_with_comments_and_empty_lines(self, temp_dir):
        """Test loading cookies file with comments and empty lines."""
        cookies_file = temp_dir / "cookies.txt"

        cookie_content = """# This is a comment
# Another comment

.youtube.com\tTRUE\t/\tFALSE\t1735689600\tSIDCC\tvalue1

# More comments
.google.com\tTRUE\t/\tFALSE\t1735689600\tNID\tvalue2


"""
        cookies_file.write_text(cookie_content)

        cookies = load_cookies_from_netscape_file(cookies_file)

        assert cookies is not None
        assert len(cookies) == 2
        assert cookies["SIDCC"] == "value1"
        assert cookies["NID"] == "value2"

    def test_load_cookies_invalid_format(self, temp_dir):
        """Test handling of invalid cookie format."""
        cookies_file = temp_dir / "cookies.txt"

        cookie_content = """# Valid cookie
.youtube.com\tTRUE\t/\tFALSE\t1735689600\tvalid_cookie\tvalue1
# Invalid cookie (missing fields)
.youtube.com\tTRUE\t/\tinvalid_line
# Another valid cookie
.google.com\tTRUE\t/\tFALSE\t1735689600\tanother_cookie\tvalue2
"""
        cookies_file.write_text(cookie_content)

        cookies = load_cookies_from_netscape_file(cookies_file)

        # Should still load valid cookies and skip invalid ones
        assert cookies is not None
        assert len(cookies) == 2
        assert cookies["valid_cookie"] == "value1"
        assert cookies["another_cookie"] == "value2"

    def test_load_cookies_no_youtube_cookies(self, temp_dir):
        """Test loading cookies file with no YouTube/Google cookies."""
        cookies_file = temp_dir / "cookies.txt"

        cookie_content = """example.com\tTRUE\t/\tFALSE\t1735689600\tcookie1\tvalue1
other.com\tTRUE\t/\tFALSE\t1735689600\tcookie2\tvalue2
"""
        cookies_file.write_text(cookie_content)

        cookies = load_cookies_from_netscape_file(cookies_file)

        # Should return None when no YouTube/Google cookies are found
        assert cookies is None

    def test_load_cookies_file_not_found(self, temp_dir):
        """Test handling of non-existent cookie file."""
        cookies_file = temp_dir / "nonexistent.txt"

        cookies = load_cookies_from_netscape_file(cookies_file)

        assert cookies is None

    def test_load_cookies_file_read_error(self, temp_dir):
        """Test handling of file read errors."""
        cookies_file = temp_dir / "cookies.txt"
        cookies_file.write_text("content")
        cookies_file.chmod(0o000)  # Remove all permissions

        try:
            cookies = load_cookies_from_netscape_file(cookies_file)
            assert cookies is None
        finally:
            cookies_file.chmod(0o644)  # Restore permissions for cleanup


class TestMakeHttpRequestWithCookies:
    """Test make_http_request function with cookie support."""

    @patch("post_archiver_improved.utils.urlopen")
    def test_request_with_cookies(self, mock_urlopen):
        """Test HTTP request with cookies."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({"success": True}).encode("utf-8")
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        cookies = {"SIDCC": "value1", "NID": "value2", "__Secure-1PSIDCC": "value3"}

        result = make_http_request("https://example.com/api", cookies=cookies)

        assert result == {"success": True}

        # Check that cookies were added to headers
        call_args = mock_urlopen.call_args[0][0]
        cookie_header = call_args.get_header("Cookie")
        assert cookie_header is not None

        # Check that all cookies are present in the header
        assert "SIDCC=value1" in cookie_header
        assert "NID=value2" in cookie_header
        assert "__Secure-1PSIDCC=value3" in cookie_header

    @patch("post_archiver_improved.utils.urlopen")
    def test_request_without_cookies(self, mock_urlopen):
        """Test HTTP request without cookies (existing behavior)."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({"success": True}).encode("utf-8")
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = make_http_request("https://example.com/api")

        assert result == {"success": True}

        # Check that no cookie header was added
        call_args = mock_urlopen.call_args[0][0]
        cookie_header = call_args.get_header("Cookie")
        assert cookie_header is None

    @patch("post_archiver_improved.utils.urlopen")
    def test_request_with_empty_cookies(self, mock_urlopen):
        """Test HTTP request with empty cookies dictionary."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({"success": True}).encode("utf-8")
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = make_http_request("https://example.com/api", cookies={})

        assert result == {"success": True}

        # Check that no cookie header was added for empty cookies
        call_args = mock_urlopen.call_args[0][0]
        cookie_header = call_args.get_header("Cookie")
        assert cookie_header is None

    @patch("post_archiver_improved.utils.urlopen")
    def test_request_cookies_with_existing_headers(self, mock_urlopen):
        """Test HTTP request with both cookies and existing headers."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({"success": True}).encode("utf-8")
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        headers = {"Authorization": "Bearer token"}
        cookies = {"session": "abc123"}

        result = make_http_request(
            "https://example.com/api", headers=headers, cookies=cookies
        )

        assert result == {"success": True}

        # Check that both custom headers and cookies are present
        call_args = mock_urlopen.call_args[0][0]
        assert call_args.get_header("Authorization") == "Bearer token"
        assert call_args.get_header("Cookie") == "session=abc123"


class TestCookieIntegration:
    """Test integration of cookie functionality with other components."""

    def test_cookie_header_formatting(self):
        """Test cookie header string formatting."""
        from post_archiver_improved.utils import _format_cookie_header

        cookies = {"cookie1": "value1", "cookie2": "value2", "cookie3": "value3"}

        header = _format_cookie_header(cookies)

        # Check that all cookies are present
        assert "cookie1=value1" in header
        assert "cookie2=value2" in header
        assert "cookie3=value3" in header

        # Check format (should be semicolon-separated)
        assert header.count(";") == 2

    def test_cookie_header_empty(self):
        """Test cookie header formatting with empty cookies."""
        from post_archiver_improved.utils import _format_cookie_header

        header = _format_cookie_header({})
        assert header == ""

    def test_cookie_header_single_cookie(self):
        """Test cookie header formatting with single cookie."""
        from post_archiver_improved.utils import _format_cookie_header

        cookies = {"single": "value"}
        header = _format_cookie_header(cookies)
        assert header == "single=value"


if __name__ == "__main__":
    pytest.main([__file__])

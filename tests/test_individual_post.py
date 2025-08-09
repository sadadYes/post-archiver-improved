"""
Tests for individual post functionality.

This module tests the new individual post scraping features.
"""

from post_archiver_improved.utils import (
    extract_post_id_from_url,
    is_post_url_or_id,
    validate_post_id,
)


class TestPostUtilities:
    """Test post utility functions."""

    def test_extract_post_id_from_url_valid(self):
        """Test extracting post ID from valid URLs."""
        test_cases = [
            (
                "https://www.youtube.com/post/UgkxMVl0vgxzNvE3I52s0oKlEHO3KyfocebU",
                "UgkxMVl0vgxzNvE3I52s0oKlEHO3KyfocebU",
            ),
            ("https://youtube.com/post/UgkABC123-_xyz", "UgkABC123-_xyz"),
            (
                "https://m.youtube.com/post/Ugk1234567890123456789012345678901234",
                "Ugk1234567890123456789012345678901234",
            ),
        ]

        for url, expected_id in test_cases:
            result = extract_post_id_from_url(url)
            assert result == expected_id, (
                f"Expected {expected_id}, got {result} for URL {url}"
            )

    def test_extract_post_id_from_url_invalid(self):
        """Test extracting post ID from invalid URLs."""
        invalid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/channel/UC123456789",
            "https://www.youtube.com/",
            "invalid_url",
            "",
            None,
        ]

        for url in invalid_urls:
            result = extract_post_id_from_url(url)
            assert result is None, f"Expected None for invalid URL: {url}"

    def test_validate_post_id_valid(self):
        """Test validation of valid post IDs."""
        valid_ids = [
            "UgkxMVl0vgxzNvE3I52s0oKlEHO3KyfocebU",
            "Ugk1234567890123456789012345678901234",
            "UgkABC123-_xyz1234567890123456789",
            "UgkTest_Post-ID_12345678901234567890",
        ]

        for post_id in valid_ids:
            assert validate_post_id(post_id), f"Should be valid: {post_id}"

    def test_validate_post_id_invalid(self):
        """Test validation of invalid post IDs."""
        invalid_ids = [
            "NotStartingWithUgk123456789012345678901",  # Wrong prefix
            "Ugk",  # Too short
            "UgkTooShort",  # Too short
            "Ugk" + "x" * 100,  # Too long
            "Ugk with spaces 123456789012345678901",  # Contains spaces
            "Ugk@invalid#chars!123456789012345678",  # Invalid characters
            "",  # Empty
            None,  # None
        ]

        for post_id in invalid_ids:
            assert not validate_post_id(post_id), f"Should be invalid: {post_id}"

    def test_is_post_url_or_id_valid_post_id(self):
        """Test is_post_url_or_id with valid post IDs."""
        post_id = "UgkxMVl0vgxzNvE3I52s0oKlEHO3KyfocebU"
        is_post, extracted_id = is_post_url_or_id(post_id)

        assert is_post is True
        assert extracted_id == post_id

    def test_is_post_url_or_id_valid_post_url(self):
        """Test is_post_url_or_id with valid post URLs."""
        post_url = "https://www.youtube.com/post/UgkxMVl0vgxzNvE3I52s0oKlEHO3KyfocebU"
        expected_id = "UgkxMVl0vgxzNvE3I52s0oKlEHO3KyfocebU"

        is_post, extracted_id = is_post_url_or_id(post_url)

        assert is_post is True
        assert extracted_id == expected_id

    def test_is_post_url_or_id_channel_inputs(self):
        """Test is_post_url_or_id with channel inputs."""
        channel_inputs = [
            "UC123456789012345678901234",  # Channel ID
            "@username",  # Channel handle
            "https://www.youtube.com/channel/UC123456789",  # Channel URL
            "https://www.youtube.com/c/channelname",  # Custom channel URL
        ]

        for channel_input in channel_inputs:
            is_post, extracted_id = is_post_url_or_id(channel_input)
            assert is_post is False, f"Should not detect as post: {channel_input}"
            assert extracted_id is None, (
                f"Should return None for channel: {channel_input}"
            )

    def test_is_post_url_or_id_invalid_inputs(self):
        """Test is_post_url_or_id with invalid inputs."""
        invalid_inputs = [
            "invalid_input",
            "",
            None,
            "https://www.example.com/post/something",
            "UgkInvalidPostID",
        ]

        for invalid_input in invalid_inputs:
            is_post, extracted_id = is_post_url_or_id(invalid_input)
            assert is_post is False, f"Should not detect as post: {invalid_input}"
            assert extracted_id is None, (
                f"Should return None for invalid: {invalid_input}"
            )

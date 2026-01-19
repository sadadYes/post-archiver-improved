"""
YouTube API client for community posts.

This module handles all interactions with YouTube's internal API endpoints
for community posts and comments.
"""

from __future__ import annotations

import base64
import gzip
import re
from typing import Any

from .constants import (
    COMMUNITY_TAB_PARAMS,
    DEFAULT_USER_AGENT,
    YOUTUBE_BASE_URL,
    YOUTUBE_BROWSE_ENDPOINT,
    YOUTUBE_CLIENT_VERSION,
    YOUTUBE_NEXT_ENDPOINT,
)
from .exceptions import APIError, NetworkError, ValidationError
from .logging_config import get_logger
from .utils import make_http_request

logger = get_logger(__name__)

# Pre-compiled regex patterns for extracting channel IDs from HTML responses
_CHANNEL_ID_PATTERNS = [
    re.compile(r'"channelId":"(UC[a-zA-Z0-9_-]{22})"'),
    re.compile(r'"browseId":"(UC[a-zA-Z0-9_-]{22})"'),
    re.compile(
        r'<link[^>]*rel="canonical"[^>]*href="[^"]*channel\/(UC[a-zA-Z0-9_-]{22})"'
    ),
    re.compile(
        r'<meta[^>]*property="og:url"[^>]*content="[^"]*channel\/(UC[a-zA-Z0-9_-]{22})"'
    ),
    re.compile(r'"externalId":"(UC[a-zA-Z0-9_-]{22})"'),
]


class YouTubeCommunityAPI:
    """
    Client for YouTube's internal community API.

    This class provides methods to interact with YouTube's internal API
    endpoints for fetching community posts and comments.
    """

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        cookies_file: str | None = None,
    ):
        """
        Initialize the YouTube API client.

        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            cookies_file: Path to Netscape format cookie file for authentication
        """
        self.base_url = YOUTUBE_BROWSE_ENDPOINT
        self.next_url = YOUTUBE_NEXT_ENDPOINT
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Load cookies if provided
        self.cookies = None
        if cookies_file:
            from pathlib import Path

            from .utils import load_cookies_from_netscape_file

            self.cookies = load_cookies_from_netscape_file(Path(cookies_file))

        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": DEFAULT_USER_AGENT,
            "X-YouTube-Client-Name": "1",
            "X-YouTube-Client-Version": YOUTUBE_CLIENT_VERSION,
            "Origin": YOUTUBE_BASE_URL,
            "Referer": f"{YOUTUBE_BASE_URL}/",
        }

        self.client_context = {
            "client": {
                "hl": "en-GB",
                "clientName": "WEB",
                "clientVersion": YOUTUBE_CLIENT_VERSION,
            },
            "user": {"lockedSafetyMode": False},
        }

        logger.debug("YouTube API client initialized")

    def _make_request(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Make a POST request to YouTube API with error handling.

        Args:
            url: API endpoint URL
            payload: Request payload

        Returns:
            API response as dictionary

        Raises:
            APIError: If the API request fails or returns an error
        """
        try:
            logger.debug(f"Making API request to {url}")
            response = make_http_request(
                url=url,
                data=payload,
                headers=self.headers,
                method="POST",
                timeout=self.timeout,
                max_retries=self.max_retries,
                retry_delay=self.retry_delay,
                cookies=self.cookies,
            )

            # Check for API-level errors
            if "error" in response:
                error_msg = response["error"].get("message", "Unknown API error")
                logger.error(f"API returned error: {error_msg}")
                raise APIError(f"YouTube API error: {error_msg}")

            return response

        except NetworkError as e:
            logger.error(f"Network error during API request: {e}")
            raise APIError(f"API request failed: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during API request: {e}")
            raise APIError(f"Unexpected API error: {e}") from e

    def resolve_channel_handle(self, handle: str) -> str:
        """
        Resolve a channel handle (@username) to a channel ID.

        Args:
            handle: Channel handle (e.g., '@username')

        Returns:
            Channel ID (e.g., 'UC123...')

        Raises:
            APIError: If handle resolution fails
            ValidationError: If handle is invalid
        """
        if not handle.startswith("@"):
            raise ValidationError(f"Invalid handle format: {handle}")

        logger.debug(f"Resolving channel handle: {handle}")

        try:
            # Construct the channel URL from the handle
            channel_url = f"{YOUTUBE_BASE_URL}/{handle}"
            logger.debug(f"Requesting channel page: {channel_url}")

            # Make a request to the channel page
            headers = {
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }

            from urllib.request import Request, urlopen

            request = Request(channel_url, headers=headers)

            with urlopen(request, timeout=self.timeout) as response:  # nosec B310
                if response.status != 200:
                    raise APIError(f"Channel page returned status {response.status}")

                # Read and decode the response
                content = response.read()
                if response.info().get("Content-Encoding") == "gzip":
                    content = gzip.decompress(content)

                html_content = content.decode("utf-8", errors="ignore")

            for pattern in _CHANNEL_ID_PATTERNS:
                matches = pattern.findall(html_content)
                if matches:
                    channel_id = matches[0]
                    logger.info(f"Resolved handle {handle} to channel ID: {channel_id}")
                    return str(channel_id)

            logger.warning(
                f"Could not resolve handle {handle} from HTML, trying alternative method"
            )
            raise APIError(f"Could not resolve channel handle {handle} to channel ID")

        except Exception as e:
            if isinstance(e, (APIError, ValidationError)):
                raise
            logger.error(f"Error resolving channel handle {handle}: {e}")
            raise APIError(f"Failed to resolve channel handle {handle}: {e}") from e

    def get_initial_data(self, channel_id: str) -> dict[str, Any]:
        """
        Get initial community tab data for a channel.

        Args:
            channel_id: YouTube channel ID or handle (@username)

        Returns:
            Initial data response

        Raises:
            APIError: If the request fails
            ValidationError: If channel_id is invalid
        """
        if not channel_id:
            raise ValidationError("Channel ID cannot be empty")

        logger.info(f"Fetching initial data for channel: {channel_id}")

        # Resolve handle to channel ID if needed
        browse_id = channel_id
        if channel_id.startswith("@"):
            logger.debug(f"Channel ID is a handle, resolving: {channel_id}")
            browse_id = self.resolve_channel_handle(channel_id)
            logger.debug(f"Resolved to channel ID: {browse_id}")

        payload = {
            "context": self.client_context,
            "browseId": browse_id,
            "params": COMMUNITY_TAB_PARAMS,  # Base64 encoded parameters for community tab
        }

        try:
            response = self._make_request(self.base_url, payload)
            logger.debug("Successfully fetched initial data")
            return response
        except APIError:
            raise
        except Exception as e:
            logger.error(f"Failed to get initial data: {e}")
            raise APIError(f"Failed to get initial data: {e}") from e

    def get_continuation_data(self, continuation_token: str) -> dict[str, Any]:
        """
        Get next batch of posts using continuation token.

        Args:
            continuation_token: Continuation token from previous response

        Returns:
            Continuation data response

        Raises:
            APIError: If the request fails
            ValidationError: If continuation_token is invalid
        """
        if not continuation_token:
            raise ValidationError("Continuation token cannot be empty")

        logger.debug(
            f"Fetching continuation data with token: {continuation_token[:20]}..."
        )

        payload = {"context": self.client_context, "continuation": continuation_token}

        try:
            response = self._make_request(self.base_url, payload)
            logger.debug("Successfully fetched continuation data")
            return response
        except APIError:
            raise
        except Exception as e:
            logger.error(f"Failed to get continuation data: {e}")
            raise APIError(f"Failed to get continuation data: {e}") from e

    def get_reply_continuation_data(self, continuation_token: str) -> dict[str, Any]:
        """
        Get next batch of replies using continuation token.

        This method uses the 'next' endpoint which is typically used for replies.

        Args:
            continuation_token: Continuation token from previous response

        Returns:
            Reply continuation data response

        Raises:
            APIError: If the request fails
            ValidationError: If continuation_token is invalid
        """
        if not continuation_token:
            raise ValidationError("Continuation token cannot be empty")

        logger.debug(
            f"Fetching reply continuation data with token: {continuation_token[:20]}..."
        )

        payload = {"context": self.client_context, "continuation": continuation_token}

        try:
            response = self._make_request(self.next_url, payload)
            logger.debug("Successfully fetched reply continuation data")
            return response
        except APIError:
            raise
        except Exception as e:
            logger.error(f"Failed to get reply continuation data: {e}")
            raise APIError(f"Failed to get reply continuation data: {e}") from e

    def get_post_detail_data(self, channel_id: str, post_id: str) -> dict[str, Any]:
        """
        Get detailed post data including comments.

        Args:
            channel_id: YouTube channel ID
            post_id: Post ID

        Returns:
            Post detail data response

        Raises:
            APIError: If the request fails
            ValidationError: If parameters are invalid
        """
        if not channel_id:
            raise ValidationError("Channel ID cannot be empty")
        if not post_id:
            raise ValidationError("Post ID cannot be empty")

        logger.debug(f"Fetching post detail data for post: {post_id}")

        try:
            # Encode parameters for post detail endpoint
            channel_bytes = channel_id.encode("utf-8")
            post_bytes = post_id.encode("utf-8")

            params_data = (
                b"\xc2\x03Z\x12"
                + bytes([len(channel_bytes)])
                + channel_bytes
                + b"\x1a"
                + bytes([len(post_bytes)])
                + post_bytes
                + b"Z"
                + bytes([len(channel_bytes)])
                + channel_bytes
            )

            params = base64.b64encode(params_data).decode("ascii")

            payload = {
                "context": self.client_context,
                "browseId": "FEpost_detail",
                "params": params,
            }

            response = self._make_request(self.base_url, payload)
            logger.debug("Successfully fetched post detail data")
            return response

        except APIError:
            raise
        except Exception as e:
            logger.error(f"Failed to get post detail data: {e}")
            raise APIError(f"Failed to get post detail data: {e}") from e

    def get_individual_post_data(self, post_id: str) -> dict[str, Any]:
        """
        Get data for an individual post by post ID.

        This method attempts to fetch post data using the post ID directly.
        If that fails, it tries to extract the channel ID first.

        Args:
            post_id: YouTube post ID

        Returns:
            Post data response

        Raises:
            APIError: If the request fails
            ValidationError: If post_id is invalid
        """
        if not post_id:
            raise ValidationError("Post ID cannot be empty")

        logger.debug(f"Fetching individual post data for post: {post_id}")

        try:
            # First, try to get the channel ID from the post URL
            channel_id = self._extract_channel_id_from_post(post_id)

            if channel_id:
                logger.debug(f"Found channel ID {channel_id} for post {post_id}")
                # Use the existing post detail method if we have channel ID
                return self.get_post_detail_data(channel_id, post_id)
            else:
                # Fallback: try direct post access with different parameter structure
                logger.debug("Channel ID not found, trying direct post access")

                post_bytes = post_id.encode("utf-8")

                # Try a different parameter structure that works for individual posts
                params_data = (
                    b"\x08\x01\x12"
                    + bytes([len(post_bytes)])
                    + post_bytes
                    + b"\x18\x01"  # Additional parameters for individual post access
                )

                params = base64.b64encode(params_data).decode("ascii")

                payload = {
                    "context": self.client_context,
                    "browseId": "FEpost_detail",
                    "params": params,
                }

                response = self._make_request(self.base_url, payload)
                logger.debug("Successfully fetched individual post data")
                return response

        except APIError:
            raise
        except Exception as e:
            logger.error(f"Failed to get individual post data: {e}")
            raise APIError(f"Failed to get individual post data: {e}") from e

    def _extract_channel_id_from_post(self, post_id: str) -> str | None:
        """
        Extract channel ID from a post by visiting the post URL.

        Args:
            post_id: YouTube post ID

        Returns:
            Channel ID if found, None otherwise
        """
        try:
            post_url = f"https://www.youtube.com/post/{post_id}"
            logger.debug(f"Attempting to extract channel ID from post URL: {post_url}")

            headers = {
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }

            from urllib.request import Request, urlopen

            request = Request(post_url, headers=headers)

            # Add cookies to the request if available
            if self.cookies:
                cookie_header = "; ".join(
                    [f"{name}={value}" for name, value in self.cookies.items()]
                )
                request.add_header("Cookie", cookie_header)
                logger.debug(f"Added {len(self.cookies)} cookies to post page request")

            with urlopen(request, timeout=self.timeout) as response:  # nosec B310
                if response.status != 200:
                    logger.warning(f"Post page returned status {response.status}")
                    return None

                # Read and decode the response
                content = response.read()
                if response.info().get("Content-Encoding") == "gzip":
                    content = gzip.decompress(content)

                html_content = content.decode("utf-8", errors="ignore")

            for pattern in _CHANNEL_ID_PATTERNS:
                matches = pattern.findall(html_content)
                if matches:
                    channel_id = str(matches[0])
                    logger.debug(f"Extracted channel ID from post page: {channel_id}")
                    return channel_id

            logger.warning(
                f"Could not extract channel ID from post page for post {post_id}"
            )
            return None

        except Exception as e:
            logger.warning(f"Error extracting channel ID from post {post_id}: {e}")
            return None

    def validate_response(
        self, response: Any, expected_keys: list[str] | None = None
    ) -> bool:
        """
        Validate API response structure.

        Args:
            response: API response to validate
            expected_keys: List of keys that should be present

        Returns:
            True if response is valid, False otherwise
        """
        if not isinstance(response, dict):
            logger.warning("Response is not a dictionary")
            return False

        if expected_keys:
            missing_keys = [key for key in expected_keys if key not in response]
            if missing_keys:
                logger.warning(f"Response missing expected keys: {missing_keys}")
                return False

        # Check for common error indicators
        if "error" in response:
            logger.warning(f"Response contains error: {response['error']}")
            return False

        return True

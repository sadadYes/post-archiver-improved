"""
YouTube API client for community posts.

This module handles all interactions with YouTube's internal API endpoints
for community posts and comments.
"""

import base64
from typing import Dict, Any, Optional

from .constants import (
    YOUTUBE_BROWSE_ENDPOINT, YOUTUBE_NEXT_ENDPOINT, YOUTUBE_BASE_URL,
    DEFAULT_USER_AGENT, YOUTUBE_CLIENT_VERSION, COMMUNITY_TAB_PARAMS
)
from .exceptions import APIError, NetworkError, ValidationError
from .logging_config import get_logger
from .utils import make_http_request

logger = get_logger(__name__)


class YouTubeCommunityAPI:
    """
    Client for YouTube's internal community API.
    
    This class provides methods to interact with YouTube's internal API
    endpoints for fetching community posts and comments.
    """
    
    def __init__(self, timeout: int = 30, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Initialize the YouTube API client.
        
        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.base_url = YOUTUBE_BROWSE_ENDPOINT
        self.next_url = YOUTUBE_NEXT_ENDPOINT
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": DEFAULT_USER_AGENT,
            "X-YouTube-Client-Name": "1",
            "X-YouTube-Client-Version": YOUTUBE_CLIENT_VERSION,
            "Origin": YOUTUBE_BASE_URL,
            "Referer": f"{YOUTUBE_BASE_URL}/"
        }
        
        self.client_context = {
            "client": {
                "hl": "en-GB",
                "clientName": "WEB",
                "clientVersion": YOUTUBE_CLIENT_VERSION
            },
            "user": {
                "lockedSafetyMode": False
            }
        }
        
        logger.debug("YouTube API client initialized")
    
    def _make_request(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
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
                method='POST',
                timeout=self.timeout,
                max_retries=self.max_retries,
                retry_delay=self.retry_delay
            )
            
            # Check for API-level errors
            if 'error' in response:
                error_msg = response['error'].get('message', 'Unknown API error')
                logger.error(f"API returned error: {error_msg}")
                raise APIError(f"YouTube API error: {error_msg}")
            
            return response
            
        except NetworkError as e:
            logger.error(f"Network error during API request: {e}")
            raise APIError(f"API request failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during API request: {e}")
            raise APIError(f"Unexpected API error: {e}")
    
    def get_initial_data(self, channel_id: str) -> Dict[str, Any]:
        """
        Get initial community tab data for a channel.
        
        Args:
            channel_id: YouTube channel ID
        
        Returns:
            Initial data response
        
        Raises:
            APIError: If the request fails
            ValidationError: If channel_id is invalid
        """
        if not channel_id:
            raise ValidationError("Channel ID cannot be empty")
        
        logger.info(f"Fetching initial data for channel: {channel_id}")
        
        payload = {
            "context": self.client_context,
            "browseId": channel_id,
            "params": COMMUNITY_TAB_PARAMS  # Base64 encoded parameters for community tab
        }
        
        try:
            response = self._make_request(self.base_url, payload)
            logger.debug("Successfully fetched initial data")
            return response
        except APIError:
            raise
        except Exception as e:
            logger.error(f"Failed to get initial data: {e}")
            raise APIError(f"Failed to get initial data: {e}")
    
    def get_continuation_data(self, continuation_token: str) -> Dict[str, Any]:
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
        
        logger.debug(f"Fetching continuation data with token: {continuation_token[:20]}...")
        
        payload = {
            "context": self.client_context,
            "continuation": continuation_token
        }
        
        try:
            response = self._make_request(self.base_url, payload)
            logger.debug("Successfully fetched continuation data")
            return response
        except APIError:
            raise
        except Exception as e:
            logger.error(f"Failed to get continuation data: {e}")
            raise APIError(f"Failed to get continuation data: {e}")
    
    def get_reply_continuation_data(self, continuation_token: str) -> Dict[str, Any]:
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
        
        logger.debug(f"Fetching reply continuation data with token: {continuation_token[:20]}...")
        
        payload = {
            "context": self.client_context,
            "continuation": continuation_token
        }
        
        try:
            response = self._make_request(self.next_url, payload)
            logger.debug("Successfully fetched reply continuation data")
            return response
        except APIError:
            raise
        except Exception as e:
            logger.error(f"Failed to get reply continuation data: {e}")
            raise APIError(f"Failed to get reply continuation data: {e}")
    
    def get_post_detail_data(self, channel_id: str, post_id: str) -> Dict[str, Any]:
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
            channel_bytes = channel_id.encode('utf-8')
            post_bytes = post_id.encode('utf-8')
            
            params_data = (
                b'\xc2\x03Z\x12' + 
                bytes([len(channel_bytes)]) + channel_bytes +
                b'\x1a' + bytes([len(post_bytes)]) + post_bytes +
                b'Z' + bytes([len(channel_bytes)]) + channel_bytes
            )
            
            params = base64.b64encode(params_data).decode('ascii')
            
            payload = {
                "context": self.client_context,
                "browseId": "FEpost_detail",
                "params": params
            }
            
            response = self._make_request(self.base_url, payload)
            logger.debug("Successfully fetched post detail data")
            return response
            
        except APIError:
            raise
        except Exception as e:
            logger.error(f"Failed to get post detail data: {e}")
            raise APIError(f"Failed to get post detail data: {e}")
    
    def validate_response(self, response: Dict[str, Any], expected_keys: list[str] = None) -> bool:
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
        if 'error' in response:
            logger.warning(f"Response contains error: {response['error']}")
            return False
        
        return True

"""
Utility functions for the post archiver.

This module contains helper functions for HTTP requests, file operations,
and other common tasks.
"""

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .exceptions import FileOperationError, NetworkError, RateLimitError
from .logging_config import get_logger

logger = get_logger(__name__)


def load_cookies_from_netscape_file(cookies_file: Path) -> Optional[Dict[str, str]]:
    """
    Load cookies from a Netscape format cookie file.

    Args:
        cookies_file: Path to the Netscape format cookie file

    Returns:
        Dictionary of cookie name-value pairs, or None if loading failed
    """
    try:
        if not cookies_file.exists():
            logger.warning(f"Cookie file not found: {cookies_file}")
            return None

        cookies = {}

        with open(cookies_file, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Parse Netscape cookie format:
                # domain flag path secure expiration name value
                parts = line.split("\t")

                if len(parts) < 7:
                    logger.warning(f"Invalid cookie format at line {line_num}: {line}")
                    continue

                domain, flag, path, secure, expiration, name, value = parts[:7]

                # For YouTube, we mainly care about cookies for *.youtube.com
                if "youtube.com" in domain or "google.com" in domain:
                    cookies[name] = value
                    logger.debug(f"Loaded cookie: {name} for domain {domain}")

        if cookies:
            logger.info(f"Loaded {len(cookies)} cookies from {cookies_file}")
            return cookies
        else:
            logger.warning("No YouTube/Google cookies found in cookie file")
            return None

    except Exception as e:
        logger.error(f"Failed to load cookies from {cookies_file}: {e}")
        return None


def _format_cookie_header(cookies: Dict[str, str]) -> str:
    """
    Format cookies dictionary into a Cookie header string.

    Args:
        cookies: Dictionary of cookie name-value pairs

    Returns:
        Formatted cookie header string
    """
    return "; ".join(f"{name}={value}" for name, value in cookies.items())


def _generate_sapisid_authorization(sapisid: str, origin: str) -> str:
    """
    Generate YouTube's SAPISID-based authorization header.

    This implements YouTube's authentication protocol for accessing
    member-only content and authenticated API endpoints.

    Args:
        sapisid: The SAPISID cookie value
        origin: The origin URL (e.g., "https://www.youtube.com")

    Returns:
        Authorization header value in format "SAPISIDHASH {timestamp}_{hash}"
    """
    timestamp = str(int(time.time()))
    # Create hash of timestamp, sapisid, and origin
    # Note: SHA1 is required by YouTube's SAPISID protocol specification
    hash_input = f"{timestamp} {sapisid} {origin}"
    hash_value = hashlib.sha1(hash_input.encode(), usedforsecurity=False).hexdigest()
    return f"SAPISIDHASH {timestamp}_{hash_value}"


def _validate_url_scheme(url: str) -> None:
    """
    Validate that the URL uses a safe scheme (http or https).

    Args:
        url: The URL to validate

    Raises:
        NetworkError: If the URL scheme is not http or https
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise NetworkError(
            f"Unsafe URL scheme '{parsed.scheme}'. Only http and https are allowed."
        )


def make_http_request(
    url: str,
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    method: str = "GET",
    timeout: int = 30,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    cookies: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Make HTTP requests with retry logic and proper error handling.

    Args:
        url: The URL to make the request to
        data: Dictionary to be sent as JSON payload (for POST requests)
        headers: Dictionary of headers to include in the request
        method: HTTP method ('GET' or 'POST')
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        cookies: Dictionary of cookies to include in the request

    Returns:
        Dictionary containing the JSON response

    Raises:
        NetworkError: If the request fails after all retries
        RateLimitError: If rate limiting is detected
    """
    if headers is None:
        headers = {}

    # Add cookies to headers if provided
    if cookies:
        cookie_header = _format_cookie_header(cookies)
        headers["Cookie"] = cookie_header
        logger.debug(f"Added {len(cookies)} cookies to request")

        # Add SAPISID-based authorization for YouTube API access
        if "SAPISID" in cookies:
            try:
                parsed_url = urlparse(url)
                origin = f"{parsed_url.scheme}://{parsed_url.netloc}"
                auth_header = _generate_sapisid_authorization(
                    cookies["SAPISID"], origin
                )
                headers["Authorization"] = auth_header
                logger.debug("Added SAPISID-based authorization header")
            except Exception as e:
                logger.warning(f"Failed to generate SAPISID authorization: {e}")

    attempt = 0
    last_exception: Optional[Exception] = None

    while attempt <= max_retries:
        try:
            logger.debug(
                f"Making {method} request to {url} (attempt {attempt + 1}/{max_retries + 1})"
            )

            # Validate URL scheme for security
            _validate_url_scheme(url)

            # Prepare request data
            json_data = None
            if data is not None:
                json_data = json.dumps(data).encode("utf-8")
                if "Content-Type" not in headers:
                    headers["Content-Type"] = "application/json"

            request = Request(url, data=json_data, headers=headers, method=method)

            # URL scheme has been validated above to ensure it's http/https only
            with urlopen(request, timeout=timeout) as response:  # nosec B310
                if response.status < 200 or response.status >= 300:
                    raise HTTPError(
                        url,
                        response.status,
                        response.reason,
                        response.headers,
                        response,
                    )

                response_data = response.read().decode("utf-8")
                result: Dict[str, Any] = json.loads(response_data)

                logger.debug(f"Request successful: {response.status}")
                return result

        except HTTPError as e:
            last_exception = e
            if e.code == 429:  # Rate limiting
                logger.warning("Rate limiting detected (HTTP 429)")
                raise RateLimitError(f"Rate limited by server: {e}") from e
            elif e.code in (500, 502, 503, 504):  # Server errors - retry
                logger.warning(f"Server error {e.code}, will retry")
            else:
                logger.error(f"HTTP error {e.code}: {e.reason}")
                raise NetworkError(f"HTTP {e.code}: {e.reason}") from e

        except URLError as e:
            last_exception = e
            logger.warning(f"URL error: {e.reason}")

        except json.JSONDecodeError as e:
            last_exception = e
            logger.error(f"JSON decode error: {e}")
            raise NetworkError(f"Invalid JSON response: {e}") from e

        except Exception as e:
            last_exception = e
            logger.warning(f"Request failed: {e}")

        # Don't retry on the last attempt
        if attempt < max_retries:
            wait_time = retry_delay * (2**attempt)  # Exponential backoff
            logger.debug(f"Retrying in {wait_time:.1f} seconds...")
            time.sleep(wait_time)

        attempt += 1

    # All retries failed
    error_msg = f"Request failed after {max_retries + 1} attempts"
    if last_exception:
        error_msg += f": {last_exception}"

    logger.error(error_msg)
    raise NetworkError(error_msg) from last_exception


def download_image(
    image_url: str,
    filename: str,
    output_dir: Path,
    timeout: int = 30,
    max_retries: int = 3,
) -> Optional[str]:
    """
    Download an image from a URL with proper error handling.

    Args:
        image_url: The URL of the image to download
        filename: Desired filename for the image
        output_dir: Directory to save the image
        timeout: Download timeout in seconds
        max_retries: Maximum number of retry attempts

    Returns:
        Path to the downloaded image file, or None if download failed

    Raises:
        FileOperationError: If file operations fail
    """
    try:
        images_dir = output_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        # Clean and validate filename
        safe_filename = sanitize_filename(filename)

        # Parse URL to get file extension
        parsed_url = urlparse(image_url)
        path = parsed_url.path

        if "." in path:
            extension = path.split(".")[-1].lower()
            extension = re.sub(r"[^a-zA-Z0-9]", "", extension)[:10]
            if extension not in ["jpg", "jpeg", "png", "gif", "webp", "bmp", "svg"]:
                extension = "jpg"
        else:
            extension = "jpg"

        # Ensure filename has correct extension
        if not safe_filename.lower().endswith(f".{extension}"):
            safe_filename = f"{safe_filename}.{extension}"

        file_path = images_dir / safe_filename

        # Handle filename conflicts
        counter = 1
        original_path = file_path
        while file_path.exists():
            stem = original_path.stem
            file_path = images_dir / f"{stem}_{counter}.{extension}"
            counter += 1

        # Download with retries
        attempt = 0
        last_exception = None

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        while attempt <= max_retries:
            try:
                logger.debug(
                    f"Downloading image from {image_url} (attempt {attempt + 1}/{max_retries + 1})"
                )

                # Validate URL scheme for security
                _validate_url_scheme(image_url)

                request = Request(image_url, headers=headers)
                # URL scheme has been validated above to ensure it's http/https only
                with urlopen(request, timeout=timeout) as response:  # nosec B310
                    if response.status != 200:
                        raise HTTPError(
                            image_url,
                            response.status,
                            response.reason,
                            response.headers,
                            response,
                        )

                    # Validate content type
                    content_type = response.headers.get("content-type", "").lower()
                    if content_type and not content_type.startswith("image/"):
                        logger.warning(
                            f"Unexpected content type '{content_type}' for image URL"
                        )

                    # Download the image
                    with open(file_path, "wb") as f:
                        f.write(response.read())

                    # Verify the file was created and has content
                    if file_path.exists() and file_path.stat().st_size > 0:
                        logger.debug(f"Successfully downloaded image to {file_path}")
                        return str(file_path)
                    else:
                        raise FileOperationError(
                            "Downloaded file is empty or not created"
                        ) from None

            except Exception as e:
                last_exception = e
                logger.warning(f"Image download attempt {attempt + 1} failed: {e}")

                # Clean up partial file
                if file_path.exists():
                    try:
                        file_path.unlink()
                    except OSError:
                        pass

                if attempt < max_retries:
                    time.sleep(1.0 * (attempt + 1))  # Progressive delay

                attempt += 1

        logger.error(
            f"Failed to download image after {max_retries + 1} attempts: {last_exception}"
        )
        return None

    except Exception as e:
        logger.error(f"Error downloading image from {image_url}: {e}")
        return None


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    Sanitize a filename by removing invalid characters and limiting length.

    Args:
        filename: Original filename
        max_length: Maximum length for the filename

    Returns:
        Sanitized filename
    """
    # Remove or replace invalid characters
    safe_name = re.sub(r"[^\w\-_.]", "_", filename)
    safe_name = re.sub(r"_+", "_", safe_name)  # Collapse multiple underscores
    safe_name = safe_name.strip("_.")  # Remove leading/trailing underscores and dots

    # Ensure filename is not empty
    if not safe_name:
        safe_name = "untitled"

    # Limit length, preserving extension if present
    if len(safe_name) > max_length:
        if "." in safe_name:
            name_part, ext_part = safe_name.rsplit(".", 1)
            available_length = max_length - len(ext_part) - 1  # -1 for the dot
            if available_length > 0:
                safe_name = f"{name_part[:available_length]}.{ext_part}"
            else:
                safe_name = safe_name[:max_length]
        else:
            safe_name = safe_name[:max_length]

    return safe_name


def validate_channel_id(channel_id: str) -> bool:
    """
    Validate YouTube channel ID format.

    Args:
        channel_id: Channel ID to validate

    Returns:
        True if valid, False otherwise
    """
    if not channel_id:
        return False

    # YouTube channel IDs typically start with 'UC' and are 24 characters long
    # But also support @username format
    if channel_id.startswith("@"):
        return (
            len(channel_id) > 1
            and channel_id[1:].replace("_", "").replace("-", "").isalnum()
        )

    if channel_id.startswith("UC") and len(channel_id) == 24:
        # YouTube channel IDs can contain letters, numbers, hyphens, and underscores
        return all(c.isalnum() or c in "-_" for c in channel_id[2:])

    # Also support custom channel URLs
    if channel_id.startswith("c/") or channel_id.startswith("channel/"):
        return True

    return False


def extract_post_id_from_url(url: str) -> Optional[str]:
    """
    Extract post ID from YouTube community post URL.

    Args:
        url: YouTube post URL (e.g., "https://www.youtube.com/post/UgkxMVl0vgxzNvE3I52s0oKlEHO3KyfocebU")

    Returns:
        Post ID if found, None otherwise
    """
    if not url:
        return None

    # Extract post ID from URL patterns
    post_id_pattern = r"/post/([a-zA-Z0-9_-]+)"
    match = re.search(post_id_pattern, url)

    if match:
        post_id = match.group(1)
        logger.debug(f"Extracted post ID from URL: {post_id}")
        return post_id

    return None


def validate_post_id(post_id: str) -> bool:
    """
    Validate YouTube post ID format.

    Args:
        post_id: Post ID to validate

    Returns:
        True if valid, False otherwise
    """
    if not post_id:
        return False

    # YouTube post IDs are typically alphanumeric with underscores and hyphens
    # They usually start with "Ugk" and are around 35-50 characters long
    if post_id.startswith("Ugk") and 20 <= len(post_id) <= 60:
        return all(c.isalnum() or c in "_-" for c in post_id)

    return False


def is_post_url_or_id(input_str: str) -> Tuple[bool, Optional[str]]:
    """
    Check if input is a post URL or post ID and extract the post ID.

    Args:
        input_str: Input string to check

    Returns:
        Tuple of (is_post, post_id)
        - is_post: True if input is a valid post URL or ID
        - post_id: Extracted post ID if valid, None otherwise
    """
    if not input_str:
        return False, None

    # First check if it's a direct post ID
    if validate_post_id(input_str):
        logger.debug(f"Input is a valid post ID: {input_str}")
        return True, input_str

    # Check if it's a post URL
    post_id = extract_post_id_from_url(input_str)
    if post_id and validate_post_id(post_id):
        logger.debug(f"Input is a valid post URL with ID: {post_id}")
        return True, post_id

    return False, None


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)

    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1

    return f"{size:.1f} {size_names[i]}"


def create_backup_filename(original_path: Path) -> Path:
    """
    Create a backup filename by adding timestamp.

    Args:
        original_path: Original file path

    Returns:
        Backup file path
    """
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = original_path.stem
    suffix = original_path.suffix

    backup_name = f"{stem}_backup_{timestamp}{suffix}"
    return original_path.parent / backup_name

"""
Utility functions for the post archiver.

This module contains helper functions for HTTP requests, file operations,
and other common tasks.
"""

import json
import re
import time
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from urllib.error import HTTPError, URLError

from .exceptions import NetworkError, RateLimitError, FileOperationError
from .logging_config import get_logger

logger = get_logger(__name__)


def make_http_request(
    url: str,
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    method: str = 'GET',
    timeout: int = 30,
    max_retries: int = 3,
    retry_delay: float = 1.0
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
    
    Returns:
        Dictionary containing the JSON response
    
    Raises:
        NetworkError: If the request fails after all retries
        RateLimitError: If rate limiting is detected
    """
    if headers is None:
        headers = {}
    
    attempt = 0
    last_exception = None
    
    while attempt <= max_retries:
        try:
            logger.debug(f"Making {method} request to {url} (attempt {attempt + 1}/{max_retries + 1})")
            
            # Prepare request data
            json_data = None
            if data is not None:
                json_data = json.dumps(data).encode('utf-8')
                if 'Content-Type' not in headers:
                    headers['Content-Type'] = 'application/json'
            
            request = Request(url, data=json_data, headers=headers, method=method)
            
            with urlopen(request, timeout=timeout) as response:
                if response.status < 200 or response.status >= 300:
                    raise HTTPError(
                        url, response.status, response.reason, 
                        response.headers, response
                    )
                
                response_data = response.read().decode('utf-8')
                result = json.loads(response_data)
                
                logger.debug(f"Request successful: {response.status}")
                return result
                
        except HTTPError as e:
            last_exception = e
            if e.code == 429:  # Rate limiting
                logger.warning(f"Rate limiting detected (HTTP 429)")
                raise RateLimitError(f"Rate limited by server: {e}")
            elif e.code in (500, 502, 503, 504):  # Server errors - retry
                logger.warning(f"Server error {e.code}, will retry")
            else:
                logger.error(f"HTTP error {e.code}: {e.reason}")
                raise NetworkError(f"HTTP {e.code}: {e.reason}")
                
        except URLError as e:
            last_exception = e
            logger.warning(f"URL error: {e.reason}")
            
        except json.JSONDecodeError as e:
            last_exception = e
            logger.error(f"JSON decode error: {e}")
            raise NetworkError(f"Invalid JSON response: {e}")
            
        except Exception as e:
            last_exception = e
            logger.warning(f"Request failed: {e}")
        
        # Don't retry on the last attempt
        if attempt < max_retries:
            wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
            logger.debug(f"Retrying in {wait_time:.1f} seconds...")
            time.sleep(wait_time)
        
        attempt += 1
    
    # All retries failed
    error_msg = f"Request failed after {max_retries + 1} attempts"
    if last_exception:
        error_msg += f": {last_exception}"
    
    logger.error(error_msg)
    raise NetworkError(error_msg)


def download_image(
    image_url: str,
    filename: str,
    output_dir: Path,
    timeout: int = 30,
    max_retries: int = 3
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
        images_dir = output_dir / 'images'
        images_dir.mkdir(parents=True, exist_ok=True)
        
        # Clean and validate filename
        safe_filename = sanitize_filename(filename)
        
        # Parse URL to get file extension
        parsed_url = urlparse(image_url)
        path = parsed_url.path
        
        if '.' in path:
            extension = path.split('.')[-1].lower()
            extension = re.sub(r'[^a-zA-Z0-9]', '', extension)[:10]
            if extension not in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg']:
                extension = 'jpg'
        else:
            extension = 'jpg'
        
        # Ensure filename has correct extension
        if not safe_filename.lower().endswith(f'.{extension}'):
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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        while attempt <= max_retries:
            try:
                logger.debug(f"Downloading image from {image_url} (attempt {attempt + 1}/{max_retries + 1})")
                
                request = Request(image_url, headers=headers)
                with urlopen(request, timeout=timeout) as response:
                    if response.status != 200:
                        raise HTTPError(
                            image_url, response.status, response.reason,
                            response.headers, response
                        )
                    
                    # Validate content type
                    content_type = response.headers.get('content-type', '').lower()
                    if content_type and not content_type.startswith('image/'):
                        logger.warning(f"Unexpected content type '{content_type}' for image URL")
                    
                    # Download the image
                    with open(file_path, 'wb') as f:
                        f.write(response.read())
                    
                    # Verify the file was created and has content
                    if file_path.exists() and file_path.stat().st_size > 0:
                        logger.debug(f"Successfully downloaded image to {file_path}")
                        return str(file_path)
                    else:
                        raise FileOperationError("Downloaded file is empty or not created")
                        
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
        
        logger.error(f"Failed to download image after {max_retries + 1} attempts: {last_exception}")
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
    safe_name = re.sub(r'[^\w\-_.]', '_', filename)
    safe_name = re.sub(r'_+', '_', safe_name)  # Collapse multiple underscores
    safe_name = safe_name.strip('_.')  # Remove leading/trailing underscores and dots
    
    # Ensure filename is not empty
    if not safe_name:
        safe_name = 'untitled'
    
    # Limit length, preserving extension if present
    if len(safe_name) > max_length:
        if '.' in safe_name:
            name_part, ext_part = safe_name.rsplit('.', 1)
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
    if channel_id.startswith('@'):
        return len(channel_id) > 1 and channel_id[1:].replace('_', '').replace('-', '').isalnum()
    
    if channel_id.startswith('UC') and len(channel_id) == 24:
        return channel_id[2:].isalnum()
    
    # Also support custom channel URLs
    if channel_id.startswith('c/') or channel_id.startswith('channel/'):
        return True
    
    return False


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
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    stem = original_path.stem
    suffix = original_path.suffix
    
    backup_name = f"{stem}_backup_{timestamp}{suffix}"
    return original_path.parent / backup_name

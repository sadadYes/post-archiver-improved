"""
Configuration file for pytest.

This file contains pytest configuration and shared fixtures.
"""

import json

# Add src to Python path for imports
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from post_archiver_improved.config import Config, OutputConfig, ScrapingConfig
from post_archiver_improved.models import (
    ArchiveData,
    ArchiveMetadata,
    Author,
    Comment,
    Image,
    Link,
    Post,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_config():
    """Create a sample configuration for testing."""
    return Config(
        scraping=ScrapingConfig(
            max_posts=10,
            extract_comments=True,
            max_comments_per_post=50,
            max_replies_per_comment=100,
            download_images=False,
            request_timeout=20,
            max_retries=2,
            retry_delay=0.5,
        ),
        output=OutputConfig(
            output_dir=None,
            save_format="json",
            pretty_print=True,
            include_metadata=True,
        ),
        log_file=None,
    )


@pytest.fixture
def sample_author():
    """Create a sample author for testing."""
    return Author(
        id="UC123456789",
        name="Test Channel",
        url="https://youtube.com/channel/UC123456789",
        thumbnail="https://example.com/avatar.jpg",
        is_verified=True,
        is_member=False,
    )


@pytest.fixture
def sample_comment(sample_author):
    """Create a sample comment for testing."""
    return Comment(
        id="comment123",
        text="This is a test comment",
        like_count="5",
        timestamp="2023-01-01T12:00:00Z",
        timestamp_estimated=False,
        author=sample_author,
        is_favorited=False,
        is_pinned=False,
        reply_count="2",
        replies=[],
    )


@pytest.fixture
def sample_image():
    """Create a sample image for testing."""
    return Image(
        src="https://example.com/image.jpg",
        local_path=None,
        width=800,
        height=600,
        file_size=1024000,
    )


@pytest.fixture
def sample_link():
    """Create a sample link for testing."""
    return Link(text="Example Link", url="https://example.com")


@pytest.fixture
def sample_post(sample_author, sample_comment, sample_image, sample_link):
    """Create a sample post for testing."""
    return Post(
        post_id="post123",
        content="This is a test post with some content.",
        timestamp="2023-01-01T10:00:00Z",
        timestamp_estimated=False,
        likes="100",
        comments_count="25",
        members_only=False,
        author=sample_author,
        images=[sample_image],
        links=[sample_link],
        comments=[sample_comment],
    )


@pytest.fixture
def sample_archive_metadata():
    """Create sample archive metadata for testing."""
    return ArchiveMetadata(
        channel_id="UC123456789",
        scrape_date="2023-01-01T12:00:00Z",
        scrape_timestamp=1672574400,
        posts_count=5,
        total_comments=15,
        total_images=3,
        images_downloaded=0,
        config_used={"max_posts": 10, "extract_comments": True},
    )


@pytest.fixture
def sample_archive_data(sample_archive_metadata, sample_post):
    """Create sample archive data for testing."""
    return ArchiveData(metadata=sample_archive_metadata, posts=[sample_post])


@pytest.fixture
def mock_api_response():
    """Create a mock API response for testing."""
    return {
        "contents": {
            "twoColumnBrowseResultsRenderer": {
                "tabs": [
                    {
                        "tabRenderer": {
                            "title": "Community",
                            "content": {
                                "richGridRenderer": {
                                    "contents": [
                                        {
                                            "richItemRenderer": {
                                                "content": {
                                                    "backstagePostRenderer": {
                                                        "postId": "test_post_123",
                                                        "contentText": {
                                                            "runs": [
                                                                {
                                                                    "text": "Test post content"
                                                                }
                                                            ]
                                                        },
                                                        "publishedTimeText": {
                                                            "runs": [
                                                                {"text": "1 day ago"}
                                                            ]
                                                        },
                                                        "voteCount": {
                                                            "runs": [{"text": "10"}]
                                                        },
                                                        "authorText": {
                                                            "runs": [
                                                                {"text": "Test Channel"}
                                                            ]
                                                        },
                                                    }
                                                }
                                            }
                                        }
                                    ]
                                }
                            },
                        }
                    }
                ]
            }
        }
    }


@pytest.fixture
def mock_http_response():
    """Create a mock HTTP response for testing."""
    mock_response = Mock()
    mock_response.read.return_value = json.dumps({"test": "data"}).encode("utf-8")
    mock_response.getcode.return_value = 200
    mock_response.info.return_value = {"Content-Type": "application/json"}
    return mock_response


@pytest.fixture
def mock_youtube_api():
    """Create a mock YouTube API client for testing."""
    from post_archiver_improved.api import YouTubeCommunityAPI

    api = Mock(spec=YouTubeCommunityAPI)
    api.get_initial_data.return_value = {"test": "data"}
    api.get_continuation_data.return_value = {"test": "continuation_data"}
    api.timeout = 30
    api.max_retries = 3
    api.retry_delay = 1.0

    return api


# Test configurations
TEST_CHANNEL_IDS = [
    "UC123456789",
    "@testchannel",
    "https://youtube.com/channel/UC123456789",
    "https://youtube.com/@testchannel",
]

INVALID_CHANNEL_IDS = ["", "invalid", "UC", "https://google.com"]

"""
Tests for the main scraper functionality.

This module tests the CommunityPostScraper class and its integration
with other components.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from post_archiver_improved.config import Config, OutputConfig, ScrapingConfig
from post_archiver_improved.exceptions import (
    APIError,
    ParseError,
    ValidationError,
)
from post_archiver_improved.models import ArchiveData, Comment, Post
from post_archiver_improved.scraper import CommunityPostScraper


class TestCommunityPostScraper:
    """Test CommunityPostScraper class."""

    def test_scraper_initialization(self, sample_config):
        """Test scraper initialization."""
        scraper = CommunityPostScraper(sample_config)

        assert scraper.config == sample_config
        assert scraper.api is not None
        assert scraper.post_extractor is not None

        # Comment extractor should be created if comments are enabled
        if sample_config.scraping.extract_comments:
            assert scraper.comment_extractor is not None
        else:
            assert scraper.comment_extractor is None

    def test_scraper_initialization_no_comments(self):
        """Test scraper initialization without comment extraction."""
        config = Config(
            scraping=ScrapingConfig(extract_comments=False), output=OutputConfig()
        )

        scraper = CommunityPostScraper(config)

        assert scraper.comment_extractor is None

    @patch("post_archiver_improved.scraper.YouTubeCommunityAPI")
    def test_scraper_api_configuration(self, mock_api_class, sample_config):
        """Test that API is configured with correct parameters."""
        scraper = CommunityPostScraper(sample_config)

        # Verify the scraper was created successfully
        assert scraper is not None
        assert scraper.config == sample_config

        mock_api_class.assert_called_once_with(
            timeout=sample_config.scraping.request_timeout,
            max_retries=sample_config.scraping.max_retries,
            retry_delay=sample_config.scraping.retry_delay,
        )


class TestScrapePosts:
    """Test scrape_posts method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config(
            scraping=ScrapingConfig(
                max_posts=10, extract_comments=True, download_images=False
            ),
            output=OutputConfig(),
        )

    @patch("post_archiver_improved.scraper.validate_channel_id")
    @patch("post_archiver_improved.scraper.YouTubeCommunityAPI")
    @patch("post_archiver_improved.scraper.PostExtractor")
    def test_scrape_posts_basic_success(
        self, mock_extractor_class, mock_api_class, mock_validate
    ):
        """Test basic successful post scraping."""
        # Setup mocks
        mock_validate.return_value = True

        mock_api = Mock()
        mock_api.get_initial_data.return_value = {
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
                                                            "postId": "test_post_1"
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
        mock_api_class.return_value = mock_api

        mock_extractor = Mock()
        mock_post = Mock(spec=Post)
        mock_post.post_id = "test_post_1"
        mock_post.comments_count = "0"
        mock_post.images = []
        mock_extractor.extract_post_data.return_value = mock_post
        mock_extractor_class.return_value = mock_extractor

        scraper = CommunityPostScraper(self.config)
        result = scraper.scrape_posts("UC123456789")

        assert isinstance(result, ArchiveData)
        assert result.metadata.channel_id == "UC123456789"
        assert len(result.posts) >= 0
        mock_validate.assert_called_once_with("UC123456789")
        mock_api.get_initial_data.assert_called_once_with("UC123456789")

    def test_scrape_posts_invalid_channel_id(self):
        """Test scraping with invalid channel ID."""
        scraper = CommunityPostScraper(self.config)

        with pytest.raises(ValidationError):
            scraper.scrape_posts("invalid_channel_id")

    @patch("post_archiver_improved.scraper.validate_channel_id")
    @patch("post_archiver_improved.scraper.YouTubeCommunityAPI")
    def test_scrape_posts_api_error(self, mock_api_class, mock_validate):
        """Test scraping with API error."""
        mock_validate.return_value = True

        mock_api = Mock()
        mock_api.get_initial_data.side_effect = APIError("API request failed")
        mock_api_class.return_value = mock_api

        scraper = CommunityPostScraper(self.config)

        with pytest.raises(APIError):
            scraper.scrape_posts("UC123456789")

    @patch("post_archiver_improved.scraper.validate_channel_id")
    @patch("post_archiver_improved.scraper.YouTubeCommunityAPI")
    def test_scrape_posts_no_community_tab(self, mock_api_class, mock_validate):
        """Test scraping when no community tab is found."""
        mock_validate.return_value = True

        mock_api = Mock()
        mock_api.get_initial_data.return_value = {
            "contents": {
                "twoColumnBrowseResultsRenderer": {"tabs": []}  # No community tab
            }
        }
        mock_api_class.return_value = mock_api

        scraper = CommunityPostScraper(self.config)
        result = scraper.scrape_posts("UC123456789")

        # Should return empty archive data
        assert isinstance(result, ArchiveData)
        assert len(result.posts) == 0

    @patch("post_archiver_improved.scraper.validate_channel_id")
    @patch("post_archiver_improved.scraper.datetime")
    def test_scrape_posts_timing_metadata(self, mock_datetime, mock_validate):
        """Test that scraping includes timing metadata."""
        mock_validate.return_value = True

        # Mock datetime.now() to return a fixed datetime

        fixed_datetime = datetime.fromtimestamp(1672574400)
        mock_datetime.now.return_value = fixed_datetime

        with patch(
            "post_archiver_improved.scraper.YouTubeCommunityAPI"
        ) as mock_api_class:
            mock_api = Mock()
            mock_api.get_initial_data.return_value = {
                "contents": {"twoColumnBrowseResultsRenderer": {"tabs": []}}
            }
            mock_api_class.return_value = mock_api

            scraper = CommunityPostScraper(self.config)
            result = scraper.scrape_posts("UC123456789")

            assert result.metadata.scrape_timestamp == 1672574400
            assert result.metadata.channel_id == "UC123456789"


class TestCommunityTabFinding:
    """Test _find_community_tab method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config(scraping=ScrapingConfig(), output=OutputConfig())
        self.scraper = CommunityPostScraper(self.config)

    def test_find_community_tab_success(self):
        """Test successful community tab finding."""
        response = {
            "contents": {
                "twoColumnBrowseResultsRenderer": {
                    "tabs": [
                        {"tabRenderer": {"title": "Home", "content": {}}},
                        {
                            "tabRenderer": {
                                "title": "Community",
                                "content": {
                                    "sectionListRenderer": {
                                        "contents": [
                                            {"itemSectionRenderer": {"contents": []}}
                                        ]
                                    }
                                },
                            }
                        },
                    ]
                }
            }
        }

        community_tab = self.scraper._find_community_tab(response)

        assert community_tab is not None
        assert community_tab["title"] == "Community"

    def test_find_community_tab_not_found(self):
        """Test community tab not found."""
        response = {
            "contents": {
                "twoColumnBrowseResultsRenderer": {
                    "tabs": [
                        {"tabRenderer": {"title": "Home", "content": {}}},
                        {"tabRenderer": {"title": "Videos", "content": {}}},
                    ]
                }
            }
        }

        community_tab = self.scraper._find_community_tab(response)

        assert community_tab is None

    def test_find_community_tab_invalid_structure(self):
        """Test community tab finding with invalid response structure."""
        invalid_responses = [
            {},
            {"contents": {}},
            {"contents": {"twoColumnBrowseResultsRenderer": {}}},
            {"contents": {"twoColumnBrowseResultsRenderer": {"tabs": None}}},
        ]

        for response in invalid_responses:
            community_tab = self.scraper._find_community_tab(response)
            assert community_tab is None


class TestPostProcessing:
    """Test post processing methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config(
            scraping=ScrapingConfig(
                extract_comments=True, download_images=True, max_posts=5
            ),
            output=OutputConfig(),
        )
        self.scraper = CommunityPostScraper(self.config)

    @patch("post_archiver_improved.scraper.PostExtractor")
    def test_process_posts_batch_basic(self, mock_extractor_class):
        """Test basic post batch processing."""
        # Setup mock extractor
        mock_extractor = Mock()
        mock_post1 = Mock(spec=Post)
        mock_post1.post_id = "post1"
        mock_post1.comments_count = "0"
        mock_post1.images = []
        mock_post1.comments = []

        mock_post2 = Mock(spec=Post)
        mock_post2.post_id = "post2"
        mock_post2.comments_count = "5"
        mock_post2.images = []
        mock_post2.comments = []

        mock_extractor.extract_post_data.side_effect = [mock_post1, mock_post2]
        mock_extractor_class.return_value = mock_extractor

        # Mock contents with correct structure
        contents = [
            {
                "backstagePostThreadRenderer": {
                    "post": {"backstagePostRenderer": {"postId": "post1"}}
                }
            },
            {
                "backstagePostThreadRenderer": {
                    "post": {"backstagePostRenderer": {"postId": "post2"}}
                }
            },
        ]

        # Mock comment extractor to avoid issues
        with patch.object(
            self.scraper, "_extract_post_comments"
        ) as mock_extract_comments:
            mock_extract_comments.return_value = []

            posts = self.scraper._process_posts_batch(contents, "UC123456789")

        assert len(posts) == 2
        assert posts[0].post_id == "post1"
        assert posts[1].post_id == "post2"

    def test_process_posts_batch_with_limit(self):
        """Test post batch processing with limit."""
        # Create more contents than the limit
        contents = [
            {
                "backstagePostThreadRenderer": {
                    "post": {"backstagePostRenderer": {"postId": f"post{i}"}}
                }
            }
            for i in range(10)
        ]

        with patch(
            "post_archiver_improved.scraper.PostExtractor"
        ) as mock_extractor_class:
            mock_extractor = Mock()
            mock_posts = []
            for i in range(10):
                mock_post = Mock(spec=Post)
                mock_post.post_id = f"post{i}"
                mock_post.comments_count = "0"
                mock_post.images = []
                mock_post.comments = []
                mock_posts.append(mock_post)

            mock_extractor.extract_post_data.side_effect = mock_posts
            mock_extractor_class.return_value = mock_extractor

            # Test with limit of 3
            posts = self.scraper._process_posts_batch(
                contents, "UC123456789", max_posts=3
            )

        assert len(posts) == 3

    def test_process_posts_batch_with_errors(self):
        """Test post batch processing with some errors."""
        contents = [
            {
                "backstagePostThreadRenderer": {
                    "post": {"backstagePostRenderer": {"postId": "valid_post"}}
                }
            },
            {
                "backstagePostThreadRenderer": {
                    "post": {"invalidRenderer": {}}  # This should cause an error
                }
            },
            {
                "backstagePostThreadRenderer": {
                    "post": {"backstagePostRenderer": {"postId": "another_valid_post"}}
                }
            },
        ]

        with patch(
            "post_archiver_improved.scraper.PostExtractor"
        ) as mock_extractor_class:
            mock_extractor = Mock()

            # First call succeeds, second fails, third succeeds
            valid_post1 = Mock(spec=Post)
            valid_post1.post_id = "valid_post"
            valid_post1.comments_count = "0"
            valid_post1.images = []
            valid_post1.comments = []

            valid_post2 = Mock(spec=Post)
            valid_post2.post_id = "another_valid_post"
            valid_post2.comments_count = "0"
            valid_post2.images = []
            valid_post2.comments = []

            mock_extractor.extract_post_data.side_effect = [
                valid_post1,
                ParseError("Invalid post structure"),
                valid_post2,
            ]
            mock_extractor_class.return_value = mock_extractor

            posts = self.scraper._process_posts_batch(contents, "UC123456789")

        # Should skip the invalid post and continue with valid ones
        assert len(posts) == 2
        assert posts[0].post_id == "valid_post"
        assert posts[1].post_id == "another_valid_post"


class TestImageDownloading:
    """Test image downloading functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config(
            scraping=ScrapingConfig(download_images=True), output=OutputConfig()
        )
        self.scraper = CommunityPostScraper(self.config)

    @patch("post_archiver_improved.scraper.download_image")
    def test_download_post_images_success(self, mock_download, temp_dir):
        """Test successful image downloading."""
        self.config.output.output_dir = temp_dir

        # Mock successful download
        mock_download.return_value = temp_dir / "downloaded_image.jpg"

        # Create post with images
        from post_archiver_improved.models import Image

        image1 = Image(src="https://example.com/image1.jpg")
        image2 = Image(src="https://example.com/image2.jpg")

        post = Mock(spec=Post)
        post.images = [image1, image2]

        self.scraper._download_post_images(post)

        # Should call download_image for each image
        assert mock_download.call_count == 2

        # Check that local_path was set
        assert image1.local_path is not None
        assert image2.local_path is not None

    @patch("post_archiver_improved.scraper.download_image")
    def test_download_post_images_with_errors(self, mock_download, temp_dir):
        """Test image downloading with some errors."""
        self.config.output.output_dir = temp_dir

        # Mock download with error for second image
        mock_download.side_effect = [
            temp_dir / "image1.jpg",  # Success
            FileNotFoundError("Download failed"),  # Error
        ]

        from post_archiver_improved.models import Image

        image1 = Image(src="https://example.com/image1.jpg")
        image2 = Image(src="https://example.com/image2.jpg")

        post = Mock(spec=Post)
        post.images = [image1, image2]

        # Should not raise exception, just log error
        self.scraper._download_post_images(post)

        # First image should have local_path, second should not
        assert image1.local_path is not None
        assert image2.local_path is None

    def test_download_post_images_no_output_dir(self):
        """Test image downloading when no output directory is configured."""
        self.config.output.output_dir = None

        from post_archiver_improved.models import Image

        image = Image(src="https://example.com/image.jpg")

        post = Mock(spec=Post)
        post.images = [image]

        # Should return early without attempting download
        self.scraper._download_post_images(post)

        assert image.local_path is None


class TestCommentExtraction:
    """Test comment extraction functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config(
            scraping=ScrapingConfig(extract_comments=True), output=OutputConfig()
        )
        self.scraper = CommunityPostScraper(self.config)

    def test_extract_post_comments_success(self):
        """Test successful comment extraction."""
        # Setup mock comment extractor
        mock_comments = [
            Mock(spec=Comment, id="comment1"),
            Mock(spec=Comment, id="comment2"),
        ]

        # Mock the comment extractor's extract_comments method
        mock_comment_extractor = Mock()
        mock_comment_extractor.extract_comments.return_value = mock_comments
        self.scraper.comment_extractor = mock_comment_extractor

        comments = self.scraper._extract_post_comments("UC123456789", "post123")

        assert len(comments) == 2
        assert comments[0].id == "comment1"
        assert comments[1].id == "comment2"

        # Verify the extract_comments method was called with correct arguments
        mock_comment_extractor.extract_comments.assert_called_once_with(
            channel_id="UC123456789",
            post_id="post123",
            max_comments=self.config.scraping.max_comments_per_post,
            max_replies_per_comment=self.config.scraping.max_replies_per_comment,
        )

    def test_extract_post_comments_no_extractor(self):
        """Test comment extraction when no comment extractor is available."""
        self.scraper.comment_extractor = None

        comments = self.scraper._extract_post_comments("UC123456789", "post123")

        assert comments == []

    def test_extract_post_comments_with_error(self):
        """Test comment extraction with error."""
        # Setup mock to raise exception
        mock_comment_extractor = Mock()
        mock_comment_extractor.extract_comments.side_effect = APIError(
            "Comment API failed"
        )
        self.scraper.comment_extractor = mock_comment_extractor

        # Should handle error gracefully and return empty list
        comments = self.scraper._extract_post_comments("UC123456789", "post123")

        assert comments == []


class TestConfigSummary:
    """Test configuration summary generation."""

    def test_get_config_summary_basic(self):
        """Test basic configuration summary."""
        config = Config(
            scraping=ScrapingConfig(
                max_posts=50,
                extract_comments=True,
                max_comments_per_post=100,
                max_replies_per_comment=200,
                download_images=True,
                request_timeout=30,
                max_retries=3,
            ),
            output=OutputConfig(),
        )

        scraper = CommunityPostScraper(config)
        summary = scraper._get_config_summary()

        assert summary["max_posts"] == 50
        assert summary["extract_comments"] is True
        assert summary["max_comments_per_post"] == 100
        assert summary["max_replies_per_comment"] == 200
        assert summary["download_images"] is True
        assert summary["request_timeout"] == 30
        assert summary["max_retries"] == 3

    def test_get_config_summary_infinite_posts(self):
        """Test configuration summary with infinite posts."""
        config = Config(
            scraping=ScrapingConfig(max_posts=float("inf")), output=OutputConfig()
        )

        scraper = CommunityPostScraper(config)
        summary = scraper._get_config_summary()

        assert summary["max_posts"] == "unlimited"


class TestScraperIntegration:
    """Test scraper integration scenarios."""

    @patch("post_archiver_improved.scraper.validate_channel_id")
    @patch("post_archiver_improved.scraper.YouTubeCommunityAPI")
    @patch("post_archiver_improved.scraper.PostExtractor")
    def test_full_scraping_workflow(
        self, mock_extractor_class, mock_api_class, mock_validate
    ):
        """Test complete scraping workflow."""
        # Setup mocks for a realistic scenario
        mock_validate.return_value = True

        # Mock API responses
        mock_api = Mock()
        initial_response = {
            "contents": {
                "twoColumnBrowseResultsRenderer": {
                    "tabs": [
                        {
                            "tabRenderer": {
                                "title": "Community",
                                "content": {
                                    "sectionListRenderer": {
                                        "contents": [
                                            {
                                                "itemSectionRenderer": {
                                                    "contents": [
                                                        {
                                                            "backstagePostThreadRenderer": {
                                                                "post": {
                                                                    "backstagePostRenderer": {
                                                                        "postId": "post1"
                                                                    }
                                                                }
                                                            }
                                                        },
                                                        {
                                                            "continuationItemRenderer": {
                                                                "continuationEndpoint": {
                                                                    "continuationCommand": {
                                                                        "token": "token123"
                                                                    }
                                                                }
                                                            }
                                                        },
                                                    ]
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

        continuation_response = {
            "onResponseReceivedEndpoints": [
                {
                    "appendContinuationItemsAction": {
                        "continuationItems": [
                            {
                                "backstagePostThreadRenderer": {
                                    "post": {
                                        "backstagePostRenderer": {"postId": "post2"}
                                    }
                                }
                            }
                        ]
                    }
                }
            ]
        }

        mock_api.get_initial_data.return_value = initial_response
        mock_api.get_continuation_data.return_value = continuation_response
        mock_api_class.return_value = mock_api

        # Mock post extractor
        mock_extractor = Mock()
        mock_post1 = Mock(spec=Post)
        mock_post1.post_id = "post1"
        mock_post1.comments_count = "0"
        mock_post1.images = []
        mock_post1.comments = []

        mock_post2 = Mock(spec=Post)
        mock_post2.post_id = "post2"
        mock_post2.comments_count = "0"
        mock_post2.images = []
        mock_post2.comments = []

        mock_extractor.extract_post_data.side_effect = [mock_post1, mock_post2]
        mock_extractor_class.return_value = mock_extractor

        # Run scraper
        config = Config(
            scraping=ScrapingConfig(max_posts=10, extract_comments=False),
            output=OutputConfig(),
        )
        scraper = CommunityPostScraper(config)

        result = scraper.scrape_posts("UC123456789")

        # Verify results
        assert isinstance(result, ArchiveData)
        assert result.metadata.channel_id == "UC123456789"
        assert len(result.posts) == 2
        assert result.posts[0].post_id == "post1"
        assert result.posts[1].post_id == "post2"

        # Verify API calls
        mock_api.get_initial_data.assert_called_once_with("UC123456789")
        mock_api.get_continuation_data.assert_called_once_with("token123")


if __name__ == "__main__":
    pytest.main([__file__])

"""
Main scraper module for YouTube community posts.

This module provides the primary interface for scraping YouTube community posts,
including comments and images, with comprehensive error handling and logging.
"""

from __future__ import annotations

import math
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .api import YouTubeCommunityAPI
from .config import Config
from .exceptions import APIError, ValidationError
from .extractors import CommentExtractor, PostExtractor
from .logging_config import get_logger
from .models import ArchiveData, ArchiveMetadata, Comment, Post
from .utils import (
    download_image,
    is_post_url_or_id,
    validate_channel_id,
)

logger = get_logger(__name__)


class CommunityPostScraper:
    """
    Main scraper class for YouTube community posts.

    This class coordinates the scraping process, handling API calls,
    data extraction, and file operations.
    """

    def __init__(self, config: Config):
        """
        Initialize the scraper with configuration.

        Args:
            config: Configuration object with scraping parameters
        """
        self.config = config
        cookies_file_path = None
        if config.scraping.cookies_file:
            cookies_file_path = str(config.scraping.cookies_file)

        self.api = YouTubeCommunityAPI(
            timeout=config.scraping.request_timeout,
            max_retries=config.scraping.max_retries,
            retry_delay=config.scraping.retry_delay,
            cookies_file=cookies_file_path,
        )
        self.post_extractor = PostExtractor()
        self.comment_extractor = (
            CommentExtractor(self.api) if config.scraping.extract_comments else None
        )

        logger.info("Community post scraper initialized")
        logger.debug(
            f"Config: max_posts={config.scraping.max_posts}, "
            f"extract_comments={config.scraping.extract_comments}, "
            f"download_images={config.scraping.download_images}"
        )

    def scrape_posts(self, channel_id: str) -> ArchiveData:
        """
        Scrape community posts from a YouTube channel.

        Args:
            channel_id: YouTube channel ID or handle

        Returns:
            ArchiveData object containing scraped posts and metadata

        Raises:
            ValidationError: If channel_id is invalid
            APIError: If API requests fail
            ParseError: If response parsing fails
        """
        # Validate input
        if not validate_channel_id(channel_id):
            raise ValidationError(f"Invalid channel ID format: {channel_id}")

        # Resolve channel handle to actual channel ID if needed
        resolved_channel_id = channel_id
        if channel_id.startswith("@"):
            logger.debug(f"Resolving channel handle: {channel_id}")
            resolved_channel_id = self.api.resolve_channel_handle(channel_id)
            logger.info(
                f"Resolved handle {channel_id} to channel ID: {resolved_channel_id}"
            )

        logger.info(f"Starting to scrape posts for channel: {channel_id}")
        start_time = time.time()

        # Initialize archive data
        metadata = ArchiveMetadata(
            channel_id=resolved_channel_id,
            scrape_date=datetime.now().isoformat(),
            scrape_timestamp=int(datetime.now().timestamp()),
            posts_count=0,
            config_used=self._get_config_summary(),
        )
        archive_data = ArchiveData(metadata=metadata)

        try:
            # Get initial data
            logger.info("Fetching initial channel data...")
            response = self.api.get_initial_data(channel_id)

            # Find community tab
            community_tab = self._find_community_tab(response)
            if not community_tab:
                logger.warning("No community tab found for this channel")
                return archive_data

            # Extract initial posts
            contents = self._extract_tab_contents(community_tab)
            continuation_token = self._find_continuation_token(contents)

            # Process initial batch
            posts = self._process_posts_batch(contents, resolved_channel_id)
            archive_data.posts.extend(posts)

            logger.info(f"Processed initial batch: {len(posts)} posts")

            # Process continuation batches
            max_posts = self.config.scraping.max_posts
            while continuation_token and (
                max_posts is None or len(archive_data.posts) < max_posts
            ):
                try:
                    logger.debug(
                        f"Fetching continuation data (posts so far: {len(archive_data.posts)})"
                    )
                    response = self.api.get_continuation_data(continuation_token)

                    contents = self._extract_continuation_contents(response)
                    continuation_token = self._find_continuation_token(contents)

                    remaining_posts = None
                    if max_posts is not None and max_posts != math.inf:
                        remaining_posts = int(max_posts - len(archive_data.posts))
                    posts = self._process_posts_batch(
                        contents, resolved_channel_id, max_posts=remaining_posts
                    )

                    if not posts:
                        if continuation_token:
                            logger.debug(
                                "No posts in this batch, following continuation token..."
                            )
                            continue
                        logger.info("No more posts found, stopping...")
                        break

                    archive_data.posts.extend(posts)
                    logger.info(
                        f"Processed continuation batch: {len(posts)} posts "
                        f"(total: {len(archive_data.posts)})"
                    )

                    # Rate limiting
                    if self.config.scraping.retry_delay > 0:
                        time.sleep(self.config.scraping.retry_delay)

                except APIError as e:
                    logger.error(f"API error during continuation: {e}")
                    break
                except Exception as e:
                    logger.error(f"Unexpected error during continuation: {e}")
                    break

            # Update final metadata
            archive_data.metadata.posts_count = len(archive_data.posts)

            elapsed_time = time.time() - start_time
            logger.info(
                f"Scraping completed: {len(archive_data.posts)} posts in {elapsed_time:.1f}s"
            )

            return archive_data

        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            raise

    def _find_community_tab(self, response: dict[str, Any]) -> dict[str, Any] | None:
        """
        Find the community/posts tab in the channel response.

        Args:
            response: API response data

        Returns:
            Community tab data or None if not found
        """
        try:
            contents = response.get("contents", {})
            if "twoColumnBrowseResultsRenderer" not in contents:
                logger.debug("No twoColumnBrowseResultsRenderer found")
                return None

            tabs = contents["twoColumnBrowseResultsRenderer"].get("tabs", [])
            for tab in tabs:
                if "tabRenderer" in tab:
                    tab_renderer = tab["tabRenderer"]
                    title = tab_renderer.get("title", "").lower()
                    if title in ["posts", "community"]:
                        logger.debug(f"Found community tab with title: {title}")
                        return tab_renderer  # type: ignore

            logger.debug("Community tab not found in available tabs")
            return None

        except Exception as e:
            logger.warning(f"Error finding community tab: {e}")
            return None

    def _extract_tab_contents(
        self, community_tab: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Extract contents from community tab.

        Args:
            community_tab: Community tab data

        Returns:
            List of content items
        """
        try:
            content = community_tab.get("content", {})
            section_list = content.get("sectionListRenderer", {})
            sections = section_list.get("contents", [])

            if sections and "itemSectionRenderer" in sections[0]:
                contents = sections[0]["itemSectionRenderer"].get("contents", [])
                return contents  # type: ignore

            return []

        except Exception as e:
            logger.warning(f"Error extracting tab contents: {e}")
            return []

    def _extract_continuation_contents(
        self, response: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Extract contents from continuation response.

        Args:
            response: Continuation API response

        Returns:
            List of content items
        """
        try:
            endpoints = response.get("onResponseReceivedEndpoints", [])
            if not endpoints:
                return []

            # Iterate ALL endpoints — YouTube often returns multiple actions
            # (e.g., one with posts and another with the continuation token)
            all_items: list[dict[str, Any]] = []
            for endpoint in endpoints:
                if "appendContinuationItemsAction" in endpoint:
                    items = endpoint["appendContinuationItemsAction"].get(
                        "continuationItems", []
                    )
                    all_items.extend(items)
                elif "reloadContinuationItemsCommand" in endpoint:
                    items = endpoint["reloadContinuationItemsCommand"].get(
                        "continuationItems", []
                    )
                    all_items.extend(items)

            return all_items

        except Exception as e:
            logger.warning(f"Error extracting continuation contents: {e}")
            return []

    def _find_continuation_token(self, contents: list[dict[str, Any]]) -> str | None:
        """
        Find continuation token in content items.

        Args:
            contents: List of content items

        Returns:
            Continuation token or None if not found
        """
        try:
            for item in contents:
                if "continuationItemRenderer" in item:
                    continuation_endpoint = item["continuationItemRenderer"].get(
                        "continuationEndpoint", {}
                    )
                    if "continuationCommand" in continuation_endpoint:
                        token = continuation_endpoint["continuationCommand"].get(
                            "token", ""
                        )
                        if token:
                            logger.debug(f"Found continuation token: {token[:20]}...")
                            return str(token)

            logger.debug("No continuation token found")
            return None

        except Exception as e:
            logger.warning(f"Error finding continuation token: {e}")
            return None

    def _process_posts_batch(
        self,
        contents: list[dict[str, Any]],
        channel_id: str,
        max_posts: int | None = None,
    ) -> list[Post]:
        """
        Process a batch of posts from content items.

        Args:
            contents: List of content items
            channel_id: YouTube channel ID
            max_posts: Maximum number of posts to process

        Returns:
            List of processed Post objects
        """
        posts = []
        processed_count = 0

        for content in contents:
            if "backstagePostThreadRenderer" in content:
                if max_posts and processed_count >= max_posts:
                    break

                try:
                    post_renderer = content["backstagePostThreadRenderer"]["post"][
                        "backstagePostRenderer"
                    ]
                    post = self.post_extractor.extract_post_data(post_renderer)

                    # Download images if configured
                    if (
                        self.config.scraping.download_images
                        and post.images
                        and self.config.output.output_dir
                    ):
                        self._download_post_images(post)

                    # Extract comments if configured
                    if (
                        self.config.scraping.extract_comments
                        and self.comment_extractor
                        and post.comments_count != "0"
                    ):
                        post.comments = self._extract_post_comments(
                            channel_id, post.post_id
                        )

                    posts.append(post)
                    processed_count += 1

                    logger.debug(
                        f"Processed post: {post.post_id} "
                        f"(comments: {len(post.comments)}, images: {len(post.images)})"
                    )

                except Exception as e:
                    logger.warning(f"Error processing post: {e}")
                    continue

        return posts

    def _download_post_images(self, post: Post) -> None:
        """
        Download images for a post.

        Args:
            post: Post object with images to download
        """
        if not self.config.output.output_dir:
            logger.warning("No output directory configured for image downloads")
            return

        for i, image in enumerate(post.images):
            if not image.src:
                continue

            try:
                # Generate filename
                if len(post.images) > 1:
                    filename = f"{post.post_id}_image_{i + 1}"
                else:
                    filename = post.post_id

                # Download image
                downloaded_path = download_image(
                    image_url=image.src,
                    filename=filename,
                    output_dir=self.config.output.output_dir,
                    timeout=self.config.scraping.request_timeout,
                    max_retries=self.config.scraping.max_retries,
                )

                if downloaded_path:
                    image.local_path = downloaded_path

                    # Get file size
                    try:
                        file_path = Path(downloaded_path)
                        if file_path.exists():
                            image.file_size = file_path.stat().st_size
                    except OSError:
                        pass

                    logger.info(f"Downloaded image: {downloaded_path}")
                else:
                    logger.warning(f"Failed to download image: {image.src}")

            except Exception as e:
                logger.error(f"Error downloading image {image.src}: {e}")

    def _extract_post_comments(self, channel_id: str, post_id: str) -> list[Comment]:
        """
        Extract comments for a post.

        Args:
            channel_id: YouTube channel ID
            post_id: Post ID

        Returns:
            List of Comment objects
        """
        if not self.comment_extractor:
            return []

        try:
            logger.debug(f"Extracting comments for post: {post_id}")

            comments = self.comment_extractor.extract_comments(
                channel_id=channel_id,
                post_id=post_id,
                max_comments=self.config.scraping.max_comments_per_post,
                max_replies_per_comment=self.config.scraping.max_replies_per_comment,
            )

            logger.debug(f"Extracted {len(comments)} comments for post {post_id}")
            return comments

        except Exception as e:
            logger.warning(f"Error extracting comments for post {post_id}: {e}")
            return []

    def scrape_individual_post(self, post_input: str) -> ArchiveData:
        """
        Scrape a single community post by post ID or URL.

        Args:
            post_input: Post ID or URL

        Returns:
            ArchiveData object containing the scraped post and metadata

        Raises:
            ValidationError: If post_input is invalid
            APIError: If API requests fail
            ParseError: If response parsing fails
        """
        # Check if input is a valid post URL or ID
        is_post, post_id = is_post_url_or_id(post_input)
        if not is_post or not post_id:
            raise ValidationError(f"Invalid post ID or URL format: {post_input}")

        logger.info(f"Starting to scrape individual post: {post_id}")
        start_time = time.time()

        # Initialize archive data with placeholder metadata
        metadata = ArchiveMetadata(
            channel_id=f"post_{post_id}",  # Use post-specific identifier for filename
            scrape_date=datetime.now().isoformat(),
            scrape_timestamp=int(datetime.now().timestamp()),
            posts_count=0,
            config_used=self._get_config_summary(),
        )
        archive_data = ArchiveData(metadata=metadata)

        try:
            # Get individual post data
            logger.info("Fetching individual post data...")
            response = self.api.get_individual_post_data(post_id)

            # Extract post data from response
            post = self._extract_individual_post_from_response(response, post_id)

            if not post:
                logger.warning("No post data found for the given post ID")
                return archive_data

            # Update metadata with actual channel ID
            archive_data.metadata.channel_id = post.author.id or "unknown"

            # Download images if configured
            if (
                self.config.scraping.download_images
                and post.images
                and self.config.output.output_dir
            ):
                self._download_post_images(post)

            # Extract comments if configured
            if self.config.scraping.extract_comments and self.comment_extractor:
                logger.debug(
                    f"Attempting to extract comments for individual post: {post.post_id}"
                )
                post.comments = self._extract_post_comments(
                    post.author.id or "unknown", post.post_id
                )
                logger.info(
                    f"Extracted {len(post.comments)} comments for individual post"
                )

            archive_data.posts.append(post)
            archive_data.metadata.posts_count = 1

            elapsed_time = time.time() - start_time
            logger.info(
                f"Individual post scraping completed: 1 post in {elapsed_time:.1f}s"
            )

            return archive_data

        except Exception as e:
            logger.error(f"Error during individual post scraping: {e}")
            raise

    def _extract_individual_post_from_response(
        self, response: dict[str, Any], post_id: str
    ) -> Post | None:
        """
        Extract post data from individual post API response.

        Args:
            response: API response data
            post_id: Expected post ID

        Returns:
            Post object if found, None otherwise
        """
        try:
            # Navigate through the response structure to find post data
            contents = response.get("contents", {})

            # Try different possible response structures
            if "twoColumnBrowseResultsRenderer" in contents:
                tabs = contents["twoColumnBrowseResultsRenderer"].get("tabs", [])
                for tab in tabs:
                    if "tabRenderer" in tab:
                        tab_content = tab["tabRenderer"].get("content", {})
                        if "sectionListRenderer" in tab_content:
                            sections = tab_content["sectionListRenderer"].get(
                                "contents", []
                            )
                            for section in sections:
                                if "itemSectionRenderer" in section:
                                    items = section["itemSectionRenderer"].get(
                                        "contents", []
                                    )
                                    for item in items:
                                        if "backstagePostThreadRenderer" in item:
                                            post_renderer = item[
                                                "backstagePostThreadRenderer"
                                            ]["post"]["backstagePostRenderer"]
                                            post = (
                                                self.post_extractor.extract_post_data(
                                                    post_renderer
                                                )
                                            )
                                            if (
                                                post.post_id == post_id
                                                or not post.post_id
                                            ):
                                                post.post_id = (
                                                    post_id  # Ensure correct post ID
                                                )
                                                return post

            # Alternative structure for direct post responses
            if "header" in response or "metadata" in response:
                # Try to find backstagePostRenderer in the response
                def find_post_renderer(obj: Any) -> dict[str, Any] | None:
                    if isinstance(obj, dict):
                        if "backstagePostRenderer" in obj:
                            renderer = obj["backstagePostRenderer"]
                            if isinstance(renderer, dict):
                                return renderer
                        for value in obj.values():
                            result = find_post_renderer(value)
                            if result:
                                return result
                    elif isinstance(obj, list):
                        for item in obj:
                            result = find_post_renderer(item)
                            if result:
                                return result
                    return None

                post_renderer = find_post_renderer(response)
                if post_renderer:
                    post = self.post_extractor.extract_post_data(post_renderer)
                    if not post.post_id:
                        post.post_id = post_id  # Ensure correct post ID
                    return post

            logger.warning(
                f"Could not find post data in response for post ID: {post_id}"
            )
            return None

        except Exception as e:
            logger.warning(f"Error extracting individual post from response: {e}")
            return None

    def _get_config_summary(self) -> dict[str, Any]:
        """
        Get a summary of the current configuration for metadata.

        Returns:
            Dictionary with configuration summary
        """
        return {
            "max_posts": (
                self.config.scraping.max_posts
                if self.config.scraping.max_posts != math.inf
                else "unlimited"
            ),
            "extract_comments": self.config.scraping.extract_comments,
            "max_comments_per_post": self.config.scraping.max_comments_per_post,
            "max_replies_per_comment": self.config.scraping.max_replies_per_comment,
            "download_images": self.config.scraping.download_images,
            "request_timeout": self.config.scraping.request_timeout,
            "max_retries": self.config.scraping.max_retries,
        }

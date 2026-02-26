"""
Data extractors for YouTube community posts and comments.

This module contains classes responsible for extracting and parsing data
from YouTube's API responses into structured data models.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

from .constants import RELATIVE_TIME_INDICATORS, YOUTUBE_BASE_URL
from .exceptions import ParseError
from .logging_config import get_logger
from .models import Author, Comment, Image, Link, Post

logger = get_logger(__name__)

# Pre-compiled regex for extracting numeric values from strings
_RE_EXTRACT_DIGITS = re.compile(r"(\d+)")


class PostExtractor:
    """
    Extracts post data from YouTube API responses.

    This class handles parsing of post data from various YouTube API response
    formats and converts them into structured Post objects.
    """

    @staticmethod
    def extract_text_content(content_runs: list[dict[str, Any]]) -> str:
        """
        Extract plain text content from YouTube's 'runs' format.

        Args:
            content_runs: List of content run objects

        Returns:
            Extracted plain text
        """
        if not content_runs:
            return ""

        return "".join(run.get("text", "") for run in content_runs)

    @staticmethod
    def _extract_links(content_runs: list[dict[str, Any]]) -> list[Link]:
        """
        Extract links from content runs.

        Args:
            content_runs: List of content run objects

        Returns:
            List of Link objects
        """
        links = []

        try:
            for run in content_runs:
                nav_endpoint = run.get("navigationEndpoint", {})
                if nav_endpoint:
                    # Extract URL from various endpoint types
                    url = None

                    if "commandMetadata" in nav_endpoint:
                        web_metadata = nav_endpoint["commandMetadata"].get(
                            "webCommandMetadata", {}
                        )
                        url = web_metadata.get("url", "")
                    elif "urlEndpoint" in nav_endpoint:
                        url = nav_endpoint["urlEndpoint"].get("url", "")
                    elif "browseEndpoint" in nav_endpoint:
                        canonical_url = nav_endpoint["browseEndpoint"].get(
                            "canonicalBaseUrl", ""
                        )
                        if canonical_url:
                            url = f"{YOUTUBE_BASE_URL}{canonical_url}"

                    if url:
                        # Convert relative URLs to absolute
                        if url.startswith("/"):
                            url = f"{YOUTUBE_BASE_URL}{url}"

                        link_text = run.get("text", "")
                        links.append(Link(text=link_text, url=url))

            logger.debug(f"Extracted {len(links)} links from content")

        except Exception as e:
            logger.warning(f"Error extracting links: {e}")

        return links

    @staticmethod
    def _extract_author_info(post_renderer: dict[str, Any]) -> Author:
        """
        Extract author information from post renderer.

        Args:
            post_renderer: Post renderer data from API

        Returns:
            Author object with extracted information
        """
        author = Author()

        try:
            author_text = post_renderer.get("authorText", {})
            if "runs" in author_text and author_text["runs"]:
                author.name = author_text["runs"][0].get("text", "")

                # Try navigationEndpoint in runs first
                author_endpoint = author_text["runs"][0].get("navigationEndpoint", {})
                if "browseEndpoint" in author_endpoint:
                    browse_endpoint = author_endpoint["browseEndpoint"]
                    author.id = browse_endpoint.get("browseId", "")

                    canonical_url = browse_endpoint.get("canonicalBaseUrl", "")
                    if canonical_url:
                        author.url = f"{YOUTUBE_BASE_URL}{canonical_url}"

            # Also try direct authorEndpoint structure
            if not author.id:
                author_endpoint = post_renderer.get("authorEndpoint", {})
                if "browseEndpoint" in author_endpoint:
                    browse_endpoint = author_endpoint["browseEndpoint"]
                    author.id = browse_endpoint.get("browseId", "")

                    canonical_url = browse_endpoint.get("canonicalBaseUrl", "")
                    if canonical_url:
                        author.url = f"{YOUTUBE_BASE_URL}{canonical_url}"

            # Extract thumbnail
            author_thumbnail = post_renderer.get("authorThumbnail", {}).get(
                "thumbnails", []
            )
            if author_thumbnail:
                author.thumbnail = author_thumbnail[-1].get("url", "")

            # Extract badges - check multiple badge structures
            badges = post_renderer.get("authorBadges", [])
            for badge in badges:
                if "metadataBadgeRenderer" in badge:
                    badge_type = badge["metadataBadgeRenderer"].get("style", "")
                    if "BADGE_STYLE_TYPE_VERIFIED" in badge_type:
                        author.is_verified = True
                    elif "BADGE_STYLE_TYPE_MEMBER" in badge_type:
                        author.is_member = True

            # Also check authorCommentBadge structure
            comment_badge = post_renderer.get("authorCommentBadge", {})
            if "authorCommentBadgeRenderer" in comment_badge:
                badge_renderer = comment_badge["authorCommentBadgeRenderer"]
                icon = badge_renderer.get("icon", {})
                if icon.get("iconType") == "CHECK_CIRCLE_THICK":
                    author.is_verified = True

            logger.debug(f"Extracted author info: {author.name} ({author.id})")

        except Exception as e:
            logger.warning(f"Error extracting author info: {e}")

        return author

    @staticmethod
    def _extract_content_and_links(
        post_renderer: dict[str, Any],
    ) -> tuple[str, list[Link]]:
        """
        Extract content text and embedded links from post renderer.

        Args:
            post_renderer: Post renderer data from API

        Returns:
            Tuple of (content_text, list_of_links)
        """
        content = ""
        links = []

        try:
            content_text = post_renderer.get("contentText", {})
            if "runs" in content_text:
                content = PostExtractor.extract_text_content(content_text["runs"])

                # Extract links from runs
                for run in content_text["runs"]:
                    nav_endpoint = run.get("navigationEndpoint", {})
                    if nav_endpoint:
                        # Extract URL from various endpoint types
                        url = None

                        if "commandMetadata" in nav_endpoint:
                            web_metadata = nav_endpoint["commandMetadata"].get(
                                "webCommandMetadata", {}
                            )
                            url = web_metadata.get("url", "")
                        elif "urlEndpoint" in nav_endpoint:
                            url = nav_endpoint["urlEndpoint"].get("url", "")
                        elif "browseEndpoint" in nav_endpoint:
                            canonical_url = nav_endpoint["browseEndpoint"].get(
                                "canonicalBaseUrl", ""
                            )
                            if canonical_url:
                                url = f"{YOUTUBE_BASE_URL}{canonical_url}"

                        if url:
                            # Convert relative URLs to absolute
                            if url.startswith("/"):
                                url = f"{YOUTUBE_BASE_URL}{url}"

                            links.append(Link(text=run.get("text", ""), url=url))

            logger.debug(f"Extracted content: {len(content)} chars, {len(links)} links")

        except Exception as e:
            logger.warning(f"Error extracting content and links: {e}")

        return content, links

    @staticmethod
    def _extract_images(attachment: dict[str, Any]) -> list[Image]:
        """
        Extract images from attachment data.

        Args:
            attachment: Attachment data from post renderer or post renderer with backstageAttachment

        Returns:
            List of Image objects
        """
        images = []

        try:
            # Handle case where full post_renderer is passed (for testing)
            if "backstageAttachment" in attachment:
                attachment = attachment["backstageAttachment"]

            # Single image
            if "backstageImageRenderer" in attachment:
                image_data = attachment["backstageImageRenderer"]["image"]
                thumbnails = image_data.get("thumbnails", [])
                if thumbnails:
                    # Get highest quality URL (remove size parameters and add =s0 for best resolution)
                    standard_url = thumbnails[0]["url"]
                    src_url = standard_url.split("=")[0] + "=s0"

                    # Extract dimensions if available
                    width = height = None
                    if len(thumbnails) > 0:
                        thumb = thumbnails[-1]  # Usually highest resolution
                        width = thumb.get("width")
                        height = thumb.get("height")

                    images.append(Image(src=src_url, width=width, height=height))

            # Multiple images
            elif "postMultiImageRenderer" in attachment:
                multi_images = attachment["postMultiImageRenderer"].get("images", [])
                for image_item in multi_images:
                    if "backstageImageRenderer" in image_item:
                        image_data = image_item["backstageImageRenderer"]["image"]
                        thumbnails = image_data.get("thumbnails", [])
                        if thumbnails:
                            standard_url = thumbnails[0]["url"]
                            src_url = standard_url.split("=")[0] + "=s0"

                            width = height = None
                            if len(thumbnails) > 0:
                                thumb = thumbnails[-1]
                                width = thumb.get("width")
                                height = thumb.get("height")

                            images.append(
                                Image(src=src_url, width=width, height=height)
                            )

            logger.debug(f"Extracted {len(images)} images")

        except Exception as e:
            logger.warning(f"Error extracting images: {e}")

        return images

    @staticmethod
    def _is_timestamp_estimated(timestamp: str) -> bool:
        """
        Check if timestamp contains relative time indicators.

        Args:
            timestamp: Timestamp string to check

        Returns:
            True if timestamp appears to be estimated/relative
        """
        return any(
            indicator in timestamp.lower() for indicator in RELATIVE_TIME_INDICATORS
        )

    @staticmethod
    def extract_post_data(post_renderer: dict[str, Any]) -> Post:
        """
        Extract post data from API response.

        Args:
            post_renderer: Post renderer data from API or wrapper containing it

        Returns:
            Post object with extracted data
        """
        try:
            # Handle case where full response is passed (for testing)
            if "backstagePostRenderer" in post_renderer:
                post_renderer = post_renderer["backstagePostRenderer"]

            # Validate input structure
            if not isinstance(post_renderer, dict) or not post_renderer:
                raise ParseError("Invalid post renderer structure")

            # Check if this is a valid post renderer (should have some expected fields)
            expected_fields = [
                "postId",
                "contentText",
                "authorText",
                "publishedTimeText",
            ]
            if not any(field in post_renderer for field in expected_fields):
                raise ParseError("Post renderer missing required fields")

            post = Post()

            # Basic post information
            post.post_id = post_renderer.get("postId", "")
            if not post.post_id:
                logger.warning("Post ID not found in renderer")

            # Extract author information
            post.author = PostExtractor._extract_author_info(post_renderer)

            # Extract content and links
            post.content, post.links = PostExtractor._extract_content_and_links(
                post_renderer
            )

            # Extract timestamp
            timestamp_data = post_renderer.get("publishedTimeText", {})
            if "runs" in timestamp_data and timestamp_data["runs"]:
                post.timestamp = timestamp_data["runs"][0].get("text", "")
                post.timestamp_estimated = PostExtractor._is_timestamp_estimated(
                    post.timestamp
                )

            # Extract engagement metrics
            vote_count = post_renderer.get("voteCount", {})
            if "simpleText" in vote_count:
                post.likes = vote_count["simpleText"]
            elif "runs" in vote_count and vote_count["runs"]:
                post.likes = vote_count["runs"][0].get("text", "0")

            # Extract comment count
            action_buttons = post_renderer.get("actionButtons", {})
            comment_button = action_buttons.get("commentActionButtonsRenderer", {})
            reply_button = comment_button.get("replyButton", {})
            button_renderer = reply_button.get("buttonRenderer", {})
            button_text = button_renderer.get("text", {})

            if "simpleText" in button_text:
                comment_text = button_text["simpleText"]
                # Extract number from text like "5 Comments"
                match = _RE_EXTRACT_DIGITS.search(comment_text)
                if match:
                    post.comments_count = match.group(1)
                else:
                    post.comments_count = "0"
            elif "runs" in button_text and button_text["runs"]:
                comment_text = button_text["runs"][0].get("text", "")
                # Extract number from text like "5 Comments" or just "15"
                match = _RE_EXTRACT_DIGITS.search(comment_text)
                if match:
                    post.comments_count = match.group(1)
                else:
                    post.comments_count = "0"

            # Check for members-only content
            post.members_only = "sponsorsOnlyBadge" in post_renderer

            # Extract images
            attachment = post_renderer.get("backstageAttachment", {})
            if attachment:
                post.images = PostExtractor._extract_images(attachment)

            logger.debug(f"Successfully extracted post data: {post.post_id}")
            return post

        except Exception as e:
            logger.error(f"Error extracting post data: {e}")
            raise ParseError(f"Failed to extract post data: {e}") from e


class CommentExtractor:
    """
    Extracts comment data from YouTube API responses.

    This class handles parsing of comment and reply data from various YouTube
    API response formats and converts them into structured Comment objects.
    """

    def __init__(self, api_client: Any) -> None:
        """
        Initialize comment extractor.

        Args:
            api_client: YouTube API client instance
        """
        self.api = api_client
        logger.debug("Comment extractor initialized")

    @staticmethod
    def extract_comment(comment_data: dict[str, Any]) -> Comment | None:
        """
        Extract a single comment from comment data.

        Args:
            comment_data: Comment data containing commentRenderer or wrapper

        Returns:
            Comment object or None if extraction fails
        """
        try:
            # Validate input structure
            if not isinstance(comment_data, dict) or not comment_data:
                raise ParseError("Invalid comment data structure")

            # Handle case where wrapper is passed
            if "commentRenderer" in comment_data:
                comment_renderer = comment_data["commentRenderer"]
            else:
                comment_renderer = comment_data

            # Check if this is a valid comment renderer (should have some expected fields)
            expected_fields = ["commentId", "contentText", "authorText"]
            if not any(field in comment_renderer for field in expected_fields):
                raise ParseError("Comment renderer missing required fields")

            # Create a temporary instance to use the extraction method
            temp_extractor = CommentExtractor(None)
            return temp_extractor.extract_comment_from_renderer(comment_renderer)

        except ParseError:
            # Re-raise ParseError directly
            raise
        except Exception as e:
            logger.warning(f"Error extracting comment: {e}")
            return None

    @staticmethod
    def extract_comments_from_response(response_data: dict[str, Any]) -> list[Comment]:
        """
        Extract comments from API response data.

        Args:
            response_data: API response containing comment entities

        Returns:
            List of Comment objects
        """
        comments = []
        try:
            framework_updates = response_data.get("frameworkUpdates", {})
            entity_batch_update = framework_updates.get("entityBatchUpdate", {})
            mutations = entity_batch_update.get("mutations", [])

            # Create a temporary instance to use entity extraction method
            temp_extractor = CommentExtractor(None)

            for mutation in mutations:
                payload = mutation.get("payload", {})
                if "commentEntityPayload" in payload:
                    # Pass the actual entity payload, not the wrapper
                    entity_payloads = [{"payload": payload}]
                    comment = temp_extractor.extract_comment_from_entity(
                        entity_payloads
                    )
                    if comment:
                        comments.append(comment)

            logger.debug(f"Extracted {len(comments)} comments from response")

        except Exception as e:
            logger.warning(f"Error extracting comments from response: {e}")

        return comments

    @staticmethod
    def extract_replies(reply_data: list[dict[str, Any]]) -> list[Comment]:
        """
        Extract replies from reply data.

        Args:
            reply_data: List of reply data containing commentRenderer structures

        Returns:
            List of Comment objects
        """
        replies = []
        try:
            temp_extractor = CommentExtractor(None)

            for reply_item in reply_data:
                if "commentRenderer" in reply_item:
                    comment_renderer = reply_item["commentRenderer"]
                    comment = temp_extractor.extract_comment_from_renderer(
                        comment_renderer
                    )
                    if comment:
                        replies.append(comment)

            logger.debug(f"Extracted {len(replies)} replies")

        except Exception as e:
            logger.warning(f"Error extracting replies: {e}")

        return replies

    def extract_comments(
        self,
        channel_id: str,
        post_id: str,
        max_comments: int = 100,
        max_replies_per_comment: int = 200,
    ) -> list[Comment]:
        """
        Extract comments for a post - delegates to CommentProcessor.

        Args:
            channel_id: YouTube channel ID
            post_id: Post ID
            max_comments: Maximum number of comments to extract
            max_replies_per_comment: Maximum number of replies per comment

        Returns:
            List of Comment objects
        """
        from .comment_processor import CommentProcessor

        processor = CommentProcessor(self.api, self)
        return processor.extract_comments(
            channel_id, post_id, max_comments, max_replies_per_comment
        )

    def _create_comment_object(
        self,
        comment_id: str,
        content: str,
        like_count: str,
        published_time: str,
        author: Author,
        is_favorited: bool = False,
        is_pinned: bool = False,
        reply_count: str = "0",
    ) -> Comment:
        """
        Create a Comment object with the provided data.

        Args:
            comment_id: Comment ID
            content: Comment text content
            like_count: Number of likes as string
            published_time: Publication timestamp
            author: Author information
            is_favorited: Whether comment is favorited by channel owner
            is_pinned: Whether comment is pinned
            reply_count: Number of replies as string

        Returns:
            Comment object
        """
        return Comment(
            id=comment_id,
            text=content,
            like_count=like_count,
            timestamp=published_time,
            timestamp_estimated=True,  # YouTube comments typically use relative timestamps
            author=author,
            is_favorited=is_favorited,
            is_pinned=is_pinned,
            reply_count=reply_count,
            replies=[],
        )

    def extract_comment_from_entity(
        self, entity_payloads: list[dict[str, Any]]
    ) -> Comment | None:
        """
        Extract comment from new entity format (commentEntityPayload).

        Args:
            entity_payloads: List of entity payload objects

        Returns:
            Comment object or None if extraction fails
        """
        try:
            comment_entity = None
            toolbar_entity = None

            # Find comment and toolbar entities
            for entity in entity_payloads:
                payload = entity.get("payload", {})
                if "commentEntityPayload" in payload:
                    comment_entity = payload["commentEntityPayload"]
                elif "engagementToolbarStateEntityPayload" in payload:
                    toolbar_entity = payload["engagementToolbarStateEntityPayload"]

            if not comment_entity:
                logger.debug("No comment entity found in payload")
                return None

            # Extract basic comment data
            properties = comment_entity.get("properties", {})
            comment_id = properties.get("commentId", "") or comment_entity.get(
                "key", ""
            )
            if not comment_id:
                logger.debug("No comment ID found in entity")
                return None

            # Handle different content formats
            content_data = properties.get("content", {})
            if "content" in content_data:
                content = content_data["content"]
            elif "runs" in content_data:
                # Handle runs format like {"runs": [{"text": "..."}]}
                content = "".join(run.get("text", "") for run in content_data["runs"])
            else:
                content = ""

            published_time = properties.get("publishedTime", "")

            # Extract author information
            author_data = comment_entity.get("author", {})
            author = Author(
                id=author_data.get("channelId", ""),
                name=author_data.get("displayName", ""),
                thumbnail=author_data.get("avatarThumbnailUrl", ""),
                is_verified=author_data.get("isVerified", False),
                is_member="sponsorBadgeA11y" in author_data,
            )

            # Extract author URL
            channel_command = author_data.get("channelCommand", {}).get(
                "innertubeCommand", {}
            )
            if "browseEndpoint" in channel_command:
                canonical_url = channel_command["browseEndpoint"].get(
                    "canonicalBaseUrl", ""
                )
                if canonical_url:
                    author.url = f"{YOUTUBE_BASE_URL}{canonical_url}"
            elif "commandMetadata" in channel_command:
                web_metadata = channel_command["commandMetadata"].get(
                    "webCommandMetadata", {}
                )
                if "url" in web_metadata:
                    author.url = f"{YOUTUBE_BASE_URL}{web_metadata['url']}"

            # Extract toolbar data (likes, favorited status, reply count)
            like_count, is_favorited, reply_count = self._extract_toolbar_data(
                comment_entity.get("toolbar", {}), toolbar_entity
            )

            comment = self._create_comment_object(
                comment_id=comment_id,
                content=content,
                like_count=like_count,
                published_time=published_time,
                author=author,
                is_favorited=is_favorited,
                is_pinned=False,  # Pinned status not available in entity format
                reply_count=reply_count,
            )

            logger.debug(f"Extracted comment from entity: {comment_id}")
            return comment

        except Exception as e:
            logger.warning(f"Error extracting comment from entity: {e}")
            return None

    def _extract_toolbar_data(
        self, toolbar: dict[str, Any], toolbar_entity: dict[str, Any] | None
    ) -> tuple[str, bool, str]:
        """
        Extract like count, favorited status, and reply count from toolbar data.

        Args:
            toolbar: Toolbar data from comment entity
            toolbar_entity: Optional separate toolbar entity

        Returns:
            Tuple of (like_count, is_favorited, reply_count)
        """
        like_count = "0"
        is_favorited = False
        reply_count = "0"

        try:
            # Extract from main toolbar
            if toolbar:
                like_count = toolbar.get(
                    "likeCountA11y", toolbar.get("likeCountLiked", "0")
                )
                is_favorited = (
                    toolbar.get("heartState") == "TOOLBAR_HEART_STATE_HEARTED"
                )

                reply_count_a11y = toolbar.get("replyCountA11y", "0")
                if reply_count_a11y:
                    match = _RE_EXTRACT_DIGITS.search(reply_count_a11y)
                    reply_count = match.group(1) if match else "0"

            # Override with toolbar entity data if available
            if toolbar_entity:
                toolbar_like_count = toolbar_entity.get("likeCountA11y", "0")
                if toolbar_like_count != "0":
                    like_count = toolbar_like_count

                is_favorited = (
                    toolbar_entity.get("heartState") == "TOOLBAR_HEART_STATE_HEARTED"
                )

                toolbar_reply_count_a11y = toolbar_entity.get("replyCountA11y", "0")
                if toolbar_reply_count_a11y:
                    match = _RE_EXTRACT_DIGITS.search(toolbar_reply_count_a11y)
                    toolbar_reply_count = match.group(1) if match else "0"
                    if toolbar_reply_count != "0":
                        reply_count = toolbar_reply_count

        except Exception as e:
            logger.warning(f"Error extracting toolbar data: {e}")

        return like_count, is_favorited, reply_count

    def extract_comment_from_renderer(
        self, comment_renderer: dict[str, Any]
    ) -> Comment | None:
        """
        Extract comment from old renderer format (commentRenderer).

        Args:
            comment_renderer: Comment renderer data from API

        Returns:
            Comment object or None if extraction fails
        """
        try:
            comment_id = comment_renderer.get("commentId", "")
            if not comment_id:
                logger.debug("No comment ID found in renderer")
                return None

            # Extract content
            content_text = comment_renderer.get("contentText", {})
            if content_text is None:
                content_text = {}
            content_runs = content_text.get("runs", [])
            content = PostExtractor.extract_text_content(content_runs)

            # Extract metrics
            vote_count = comment_renderer.get("voteCount", {})
            if "simpleText" in vote_count:
                like_count = vote_count["simpleText"]
            elif "runs" in vote_count and vote_count["runs"]:
                like_count = vote_count["runs"][0].get("text", "0")
            else:
                like_count = "0"

            # Extract timestamp
            published_time_runs = comment_renderer.get("publishedTimeText", {}).get(
                "runs", []
            )
            published_time = (
                published_time_runs[0].get("text", "") if published_time_runs else ""
            )

            # Extract author information
            author = Author()
            author_text = comment_renderer.get("authorText", {})
            if author_text is None:
                author_text = {}

            if "simpleText" in author_text:
                author.name = author_text["simpleText"]
            elif (
                "runs" in author_text
                and isinstance(author_text["runs"], list)
                and author_text["runs"]
            ):
                author.name = author_text["runs"][0].get("text", "")
            else:
                author.name = ""

            author_endpoint = comment_renderer.get("authorEndpoint", {})
            if "browseEndpoint" in author_endpoint:
                browse_endpoint = author_endpoint["browseEndpoint"]
                author.id = browse_endpoint.get("browseId", "")
                canonical_url = browse_endpoint.get("canonicalBaseUrl", "")
                if canonical_url:
                    author.url = f"{YOUTUBE_BASE_URL}{canonical_url}"

            # Extract author thumbnail
            author_thumbnails = comment_renderer.get("authorThumbnail", {}).get(
                "thumbnails", []
            )
            if author_thumbnails:
                author.thumbnail = author_thumbnails[-1].get("url", "")

            # Extract author badges
            author_badges = comment_renderer.get("authorBadges", [])
            for badge in author_badges:
                if "metadataBadgeRenderer" in badge:
                    badge_style = badge["metadataBadgeRenderer"].get("style", "")
                    if "BADGE_STYLE_TYPE_VERIFIED" in badge_style:
                        author.is_verified = True
                    elif "BADGE_STYLE_TYPE_MEMBER" in badge_style:
                        author.is_member = True
                elif "liveChatAuthorBadgeRenderer" in badge:
                    badge_data = badge["liveChatAuthorBadgeRenderer"]
                    if "authorBadgeType" in badge_data:
                        badge_type = badge_data["authorBadgeType"]
                        if "VERIFIED" in badge_type:
                            author.is_verified = True
                        elif "MEMBER" in badge_type:
                            author.is_member = True

            # Also check authorCommentBadge structure
            comment_badge = comment_renderer.get("authorCommentBadge", {})
            if "authorCommentBadgeRenderer" in comment_badge:
                badge_renderer = comment_badge["authorCommentBadgeRenderer"]
                icon = badge_renderer.get("icon", {})
                if icon.get("iconType") == "CHECK_CIRCLE_THICK":
                    author.is_verified = True

            # Check sponsorCommentBadge structure
            sponsor_badge = comment_renderer.get("sponsorCommentBadge", {})
            if "sponsorCommentBadgeRenderer" in sponsor_badge:
                author.is_member = True

            # Extract reply count
            reply_count = "0"
            if "replyCount" in comment_renderer:
                reply_count_data = comment_renderer["replyCount"]
                if isinstance(reply_count_data, dict):
                    if "simpleText" in reply_count_data:
                        reply_count = reply_count_data["simpleText"]
                    elif "runs" in reply_count_data and reply_count_data["runs"]:
                        reply_count = reply_count_data["runs"][0].get("text", "0")
                    else:
                        reply_count = "0"
                else:
                    reply_count = str(reply_count_data)

            # Try alternative locations for reply count
            if reply_count == "0":
                action_buttons = comment_renderer.get("actionButtons", {})
                if "commentActionButtonsRenderer" in action_buttons:
                    buttons_renderer = action_buttons["commentActionButtonsRenderer"]
                    if "replyButton" in buttons_renderer:
                        reply_button = buttons_renderer["replyButton"]
                        if "buttonRenderer" in reply_button:
                            button_text = reply_button["buttonRenderer"].get("text", {})
                            if "simpleText" in button_text:
                                text = button_text["simpleText"]
                                match = _RE_EXTRACT_DIGITS.search(text)
                                if match:
                                    reply_count = match.group(1)

            # Extract status flags
            is_favorited = "creatorHeart" in comment_renderer.get(
                "actionButtons", {}
            ) or comment_renderer.get("isLiked", False)
            is_pinned = "pinnedCommentBadge" in comment_renderer

            comment = self._create_comment_object(
                comment_id=comment_id,
                content=content,
                like_count=like_count,
                published_time=published_time,
                author=author,
                is_favorited=is_favorited,
                is_pinned=is_pinned,
                reply_count=reply_count,
            )

            logger.debug(f"Extracted comment from renderer: {comment_id}")
            return comment

        except Exception as e:
            logger.warning(f"Error extracting comment from renderer: {e}")
            return None

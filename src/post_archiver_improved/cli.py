"""
Command-line interface for the YouTube Community Posts Archiver.

This module provides a comprehensive CLI with proper argument parsing,
configuration management, and user-friendly output.
"""

import argparse
import sys
from pathlib import Path
from typing import Any

from . import __description__, __version__
from .config import load_config, save_config_to_file, update_config_from_args
from .constants import (
    DEFAULT_MAX_COMMENTS,
    DEFAULT_MAX_REPLIES,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_DELAY,
    DEFAULT_TIMEOUT,
)
from .exceptions import (
    APIError,
    FileOperationError,
    NetworkError,
    PostArchiverError,
    ValidationError,
)
from .logging_config import setup_logging
from .output import OutputManager
from .scraper import CommunityPostScraper
from .utils import format_file_size, is_post_url_or_id, validate_channel_id


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and configure the argument parser.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog="post-archiver",
        description=__description__,
        epilog="For more information, visit: https://github.com/sadadYes/post-archiver-improved",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Version
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    # Required arguments
    parser.add_argument(
        "target",
        help="YouTube channel ID, handle (@username), channel URL, post URL, or post ID",
    )

    # Scraping options
    scraping_group = parser.add_argument_group("Scraping Options")
    scraping_group.add_argument(
        "-n",
        "--num-posts",
        type=int,
        metavar="N",
        help="Maximum number of posts to scrape (default: unlimited)",
    )
    scraping_group.add_argument(
        "-c", "--comments", action="store_true", help="Extract comments for each post"
    )
    scraping_group.add_argument(
        "--max-comments",
        type=int,
        default=DEFAULT_MAX_COMMENTS,
        metavar="N",
        help=f"Maximum number of comments to extract per post (default: {DEFAULT_MAX_COMMENTS})",
    )
    scraping_group.add_argument(
        "--max-replies",
        type=int,
        default=DEFAULT_MAX_REPLIES,
        metavar="N",
        help=f"Maximum number of replies to extract per comment (default: {DEFAULT_MAX_REPLIES})",
    )
    scraping_group.add_argument(
        "-i",
        "--download-images",
        action="store_true",
        help="Download images from posts to local directory",
    )
    scraping_group.add_argument(
        "--cookies",
        type=Path,
        metavar="FILE",
        help="Path to Netscape format cookie file for accessing members-only posts",
    )

    # Output options
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "-o",
        "--output",
        type=Path,
        metavar="DIR",
        help="Output directory (default: current directory)",
    )
    output_group.add_argument(
        "--no-summary", action="store_true", help="Do not create summary report"
    )
    output_group.add_argument(
        "--compact",
        action="store_true",
        help="Save JSON in compact format (no pretty printing)",
    )

    # Configuration options
    config_group = parser.add_argument_group("Configuration Options")
    config_group.add_argument(
        "--config", type=Path, metavar="FILE", help="Configuration file path"
    )
    config_group.add_argument(
        "--save-config",
        type=Path,
        metavar="FILE",
        help="Save current configuration to file",
    )

    # Network options
    network_group = parser.add_argument_group("Network Options")
    network_group.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        metavar="SECONDS",
        help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    network_group.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_MAX_RETRIES,
        metavar="N",
        help=f"Maximum number of retry attempts (default: {DEFAULT_MAX_RETRIES})",
    )
    network_group.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_RETRY_DELAY,
        metavar="SECONDS",
        help=f"Delay between requests in seconds (default: {DEFAULT_RETRY_DELAY})",
    )

    # Logging options
    logging_group = parser.add_argument_group("Logging Options")
    logging_group.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output (INFO level)",
    )
    logging_group.add_argument(
        "--debug", action="store_true", help="Enable debug output (DEBUG level)"
    )
    logging_group.add_argument(
        "--log-file",
        type=Path,
        metavar="FILE",
        help="Log to file in addition to console",
    )
    logging_group.add_argument(
        "--quiet", action="store_true", help="Suppress all output except errors"
    )

    return parser


def normalize_channel_id(channel_id: str) -> str:
    """
    Normalize channel ID from various formats.

    Args:
        channel_id: Raw channel ID input

    Returns:
        Normalized channel ID
    """
    # Remove common URL prefixes
    channel_id = channel_id.strip()

    # Handle full YouTube URLs
    if "youtube.com/" in channel_id:
        if "/channel/" in channel_id:
            channel_id = channel_id.split("/channel/")[-1].split("/")[0]
        elif "/c/" in channel_id:
            channel_id = channel_id.split("/c/")[-1].split("/")[0]
        elif "/@" in channel_id:
            channel_id = "@" + channel_id.split("/@")[-1].split("/")[0]

    return channel_id


def print_summary(archive_data: Any, output_path: Path, args: Any) -> None:
    """
    Print summary information to console.

    Args:
        archive_data: Archive data with results
        output_path: Path to saved archive file
        args: Command line arguments
    """
    posts = archive_data.posts
    metadata = archive_data.metadata

    # Check if this was an individual post or channel scrape
    is_individual_post = len(posts) == 1 and hasattr(args, "target")

    if is_individual_post:
        print(f"\n✓ Successfully scraped individual post: {posts[0].post_id}")
        if posts[0].author.name:
            print(f"✓ Author: {posts[0].author.name}")
    else:
        print(
            f"\n✓ Successfully scraped {len(posts)} posts from channel {metadata.channel_id}"
        )

    print(f"✓ Results saved to: {output_path}")

    if output_path.exists():
        file_size = format_file_size(output_path.stat().st_size)
        print(f"✓ File size: {file_size}")

    # Comment statistics
    if args.comments:
        total_comments = sum(len(post.comments) for post in posts)
        total_replies = sum(
            sum(len(comment.replies) for comment in post.comments) for post in posts
        )
        print(
            f"✓ Comments extracted: {total_comments} comments, {total_replies} replies"
        )

    # Image statistics
    if args.download_images:
        total_images = sum(len(post.images) for post in posts)
        downloaded_images = sum(
            1 for post in posts for image in post.images if image.local_path
        )
        if total_images > 0:
            success_rate = (downloaded_images / total_images) * 100
            print(
                f"✓ Images downloaded: {downloaded_images}/{total_images} ({success_rate:.1f}%)"
            )
            if downloaded_images > 0:
                images_dir = (
                    args.output / "images" if args.output else Path.cwd() / "images"
                )
                print(f"✓ Images saved to: {images_dir}")
        else:
            print(
                "✓ No images found in the scraped posts"
                if not is_individual_post
                else "✓ No images found in the post"
            )


def handle_error(error: Exception, logger: Any) -> int:
    """
    Handle different types of errors with appropriate messages.

    Args:
        error: Exception that occurred
        logger: Logger instance

    Returns:
        Exit code
    """
    if isinstance(error, ValidationError):
        logger.error(f"Validation error: {error}")
        return 2
    elif isinstance(error, NetworkError):
        logger.error(f"Network error: {error}")
        logger.info("Please check your internet connection and try again")
        return 3
    elif isinstance(error, APIError):
        logger.error(f"YouTube API error: {error}")
        logger.info("This might be due to rate limiting or changes in YouTube's API")
        return 4
    elif isinstance(error, FileOperationError):
        logger.error(f"File operation error: {error}")
        logger.info("Please check file permissions and available disk space")
        return 5
    elif isinstance(error, PostArchiverError):
        logger.error(f"Application error: {error}")
        return 6
    else:
        logger.error(f"Unexpected error: {error}")
        logger.debug("Full traceback:", exc_info=True)
        return 1


def main() -> int:
    """
    Main entry point for the CLI application.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = create_argument_parser()
    args = parser.parse_args()

    # Set up logging
    logger = setup_logging(
        verbose=args.verbose and not args.quiet,
        debug=args.debug and not args.quiet,
        log_file=args.log_file,
    )

    if args.quiet:
        # Disable console output for quiet mode
        import logging

        logging.getLogger().handlers[0].setLevel(logging.ERROR)

    try:
        logger.info(f"Post Archiver Improved v{__version__}")
        logger.debug(f"Arguments: {vars(args)}")

        # Check if input is a post URL/ID or channel ID
        is_post, post_id = is_post_url_or_id(args.target)

        if is_post:
            # Handle individual post scraping
            logger.info(f"Detected post input: {post_id}")

            config = load_config(args.config)

            config_updates = {
                "extract_comments": args.comments,
                "max_comments_per_post": args.max_comments,
                "max_replies_per_comment": args.max_replies,
                "download_images": args.download_images,
                "cookies_file": args.cookies,
                "output_dir": args.output,
                "log_file": args.log_file,
            }

            config.scraping.request_timeout = args.timeout
            config.scraping.max_retries = args.retries
            config.scraping.retry_delay = args.delay

            config.output.pretty_print = not args.compact

            config = update_config_from_args(config, **config_updates)

            if args.save_config:
                if save_config_to_file(config, args.save_config):
                    logger.info(f"Configuration saved to: {args.save_config}")
                else:
                    logger.warning(
                        f"Failed to save configuration to: {args.save_config}"
                    )

            # Create scraper and scrape individual post
            scraper = CommunityPostScraper(config)
            logger.info(f"Starting individual post scrape: {args.target}")

            archive_data = scraper.scrape_individual_post(args.target)

        else:
            # Handle channel scraping (existing logic)
            # Validate and normalize channel ID
            channel_id = normalize_channel_id(args.target)
            if not validate_channel_id(channel_id):
                raise ValidationError(f"Invalid channel ID format: {args.target}")

            config = load_config(args.config)

            config_updates = {
                "max_posts": args.num_posts or config.scraping.max_posts,
                "extract_comments": args.comments,
                "max_comments_per_post": args.max_comments,
                "max_replies_per_comment": args.max_replies,
                "download_images": args.download_images,
                "cookies_file": args.cookies,
                "output_dir": args.output,
                "log_file": args.log_file,
            }

            config.scraping.request_timeout = args.timeout
            config.scraping.max_retries = args.retries
            config.scraping.retry_delay = args.delay

            config.output.pretty_print = not args.compact

            config = update_config_from_args(config, **config_updates)

            if args.save_config:
                if save_config_to_file(config, args.save_config):
                    logger.info(f"Configuration saved to: {args.save_config}")
                else:
                    logger.warning(
                        f"Failed to save configuration to: {args.save_config}"
                    )

            # Create scraper and start scraping
            scraper = CommunityPostScraper(config)
            logger.info(f"Starting scrape for channel: {channel_id}")

            archive_data = scraper.scrape_posts(channel_id)

        if not archive_data.posts:
            if is_post:
                logger.warning("Post not found or could not be accessed")
                if not args.quiet:
                    print(
                        "Post not found or could not be accessed. This might be because:"
                    )
                    print("- The post ID is incorrect")
                    print("- The post has been deleted")
                    print("- The post is private or members-only")
                    print("- Authentication is required (use --cookies)")
            else:
                logger.warning("No posts found for this channel")
                if not args.quiet:
                    print("No posts found for this channel. This might be because:")
                    print("- The channel has no community posts")
                    print("- The channel's community tab is not accessible")
                    print("- The channel ID is incorrect")
            return 0

        # Save results
        output_manager = OutputManager(config.output)
        output_path = output_manager.save_archive_data(archive_data)

        # Create summary report unless disabled
        if not args.no_summary:
            summary_path = output_manager.save_summary_report(archive_data)
            if summary_path:
                logger.info(f"Summary report saved: {summary_path}")

        # Print summary to console
        if not args.quiet:
            print_summary(archive_data, output_path, args)

        return 0

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 130
    except Exception as e:
        return handle_error(e, logger)


if __name__ == "__main__":
    sys.exit(main())

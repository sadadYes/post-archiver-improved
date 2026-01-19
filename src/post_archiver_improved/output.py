"""
Output handling for archive data.

This module provides functions for saving archive data in various formats
with proper error handling and backup creation.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import OutputConfig
from .exceptions import FileOperationError
from .logging_config import get_logger
from .models import ArchiveData
from .utils import create_backup_filename, format_file_size

logger = get_logger(__name__)


class OutputManager:
    """
    Manages output operations for archive data.

    This class handles saving archive data to files with proper formatting,
    backup creation, and error handling.
    """

    def __init__(self, config: OutputConfig):
        """
        Initialize output manager with configuration.

        Args:
            config: Output configuration
        """
        self.config = config
        logger.debug("Output manager initialized")

    def save_archive_data(
        self, archive_data: ArchiveData, output_path: Path | None = None
    ) -> Path:
        """
        Save archive data to a file.

        Args:
            archive_data: Archive data to save
            output_path: Optional specific output path

        Returns:
            Path to the saved file

        Raises:
            FileOperationError: If saving fails
        """
        try:
            # Determine output path
            if output_path:
                file_path = output_path
            else:
                file_path = self._generate_output_filename(
                    archive_data.metadata.channel_id
                )

            # Ensure output directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Create backup if file already exists
            if file_path.exists():
                backup_path = create_backup_filename(file_path)
                logger.info(f"Creating backup: {backup_path}")
                file_path.rename(backup_path)

            # Save data
            logger.info(f"Saving archive data to: {file_path}")
            self._save_json_file(archive_data, file_path)

            # Log file information
            if file_path.exists():
                file_size = file_path.stat().st_size
                logger.info(
                    f"Archive saved successfully: {format_file_size(file_size)}"
                )

            return file_path

        except Exception as e:
            logger.error(f"Error saving archive data: {e}")
            raise FileOperationError(f"Failed to save archive data: {e}") from e

    def _generate_output_filename(self, channel_id: str) -> Path:
        """
        Generate output filename based on channel ID and timestamp.

        Args:
            channel_id: YouTube channel ID or "post_<post_id>" for individual posts

        Returns:
            Generated file path
        """
        output_dir = self.config.output_dir or Path.cwd()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Handle individual post filename differently
        if channel_id.startswith("post_"):
            filename = f"{channel_id}_{timestamp}.json"
        else:
            filename = f"posts_{channel_id}_{timestamp}.json"

        return output_dir / filename

    def _save_json_file(self, archive_data: ArchiveData, file_path: Path) -> None:
        """
        Save archive data as JSON file.

        Args:
            archive_data: Archive data to save
            file_path: Path to save the file

        Raises:
            FileOperationError: If saving fails
        """
        try:
            data = archive_data.to_dict()

            # Configure JSON formatting
            if self.config.pretty_print:
                indent = 2
                separators = (",", ": ")
            else:
                indent = None
                separators = (",", ":")

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(
                    data, f, ensure_ascii=False, indent=indent, separators=separators
                )

            logger.debug(f"JSON file saved: {file_path}")

        except Exception as e:
            raise FileOperationError(f"Failed to save JSON file: {e}") from e

    def create_summary_report(self, archive_data: ArchiveData) -> str:
        """
        Create a summary report of the archive data.

        Args:
            archive_data: Archive data to summarize

        Returns:
            Summary report as string
        """
        try:
            metadata = archive_data.metadata
            posts = archive_data.posts

            # Calculate statistics
            total_posts = len(posts)
            total_comments = sum(len(post.comments) for post in posts)
            total_replies = sum(
                sum(len(comment.replies) for comment in post.comments) for post in posts
            )
            total_images = sum(len(post.images) for post in posts)
            images_downloaded = sum(
                1 for post in posts for image in post.images if image.local_path
            )

            # Posts with content
            posts_with_images = sum(1 for post in posts if post.images)
            posts_with_comments = sum(1 for post in posts if post.comments)
            members_only_posts = sum(1 for post in posts if post.members_only)

            # Create report
            report_lines = [
                "=" * 60,
                "ARCHIVE SUMMARY REPORT",
                "=" * 60,
                f"Channel ID: {metadata.channel_id}",
                f"Scrape Date: {metadata.scrape_date}",
                f"Scrape Duration: {self._format_duration(metadata)}",
                "",
                "POSTS STATISTICS:",
                f"  Total Posts: {total_posts}",
                f"  Posts with Images: {posts_with_images}",
                f"  Posts with Comments: {posts_with_comments}",
                f"  Members-only Posts: {members_only_posts}",
                "",
                "COMMENTS STATISTICS:",
                f"  Total Comments: {total_comments}",
                f"  Total Replies: {total_replies}",
                f"  Average Comments per Post: {total_comments / max(total_posts, 1):.1f}",
                "",
                "IMAGES STATISTICS:",
                f"  Total Images: {total_images}",
                f"  Images Downloaded: {images_downloaded}",
                f"  Download Success Rate: {(images_downloaded / max(total_images, 1)) * 100:.1f}%",
                "",
                "CONFIGURATION USED:",
            ]

            # Add configuration details
            config_used = metadata.config_used
            for key, value in config_used.items():
                report_lines.append(f"  {key.replace('_', ' ').title()}: {value}")

            report_lines.extend(["", "=" * 60])

            return "\n".join(report_lines)

        except Exception as e:
            logger.warning(f"Error creating summary report: {e}")
            return "Error generating summary report"

    def _format_duration(self, metadata: Any) -> str:
        """
        Format scrape duration from metadata.

        Args:
            metadata: Archive metadata

        Returns:
            Formatted duration string
        """
        try:
            # This would need the start time to be stored in metadata
            # For now, return a placeholder
            return "Duration not available"
        except Exception:
            return "Unknown"

    def save_summary_report(
        self, archive_data: ArchiveData, output_dir: Path | None = None
    ) -> Path | None:
        """
        Save summary report to a text file.

        Args:
            archive_data: Archive data to summarize
            output_dir: Optional output directory

        Returns:
            Path to saved report file or None if saving fails
        """
        try:
            if not output_dir:
                output_dir = self.config.output_dir or Path.cwd()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = (
                f"summary_{archive_data.metadata.channel_id}_{timestamp}.txt"
            )
            report_path = output_dir / report_filename

            report_content = self.create_summary_report(archive_data)

            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_content)

            logger.info(f"Summary report saved: {report_path}")
            return report_path

        except Exception as e:
            logger.warning(f"Failed to save summary report: {e}")
            return None


def save_posts(
    archive_data: ArchiveData,
    output_dir: Path | None = None,
    create_summary: bool = True,
) -> Path:
    """
    Convenience function to save posts with default configuration.

    Args:
        archive_data: Archive data to save
        output_dir: Optional output directory
        create_summary: Whether to create summary report

    Returns:
        Path to saved archive file

    Raises:
        FileOperationError: If saving fails
    """
    from .config import OutputConfig

    config = OutputConfig(output_dir=output_dir)
    output_manager = OutputManager(config)

    # Save main archive file
    archive_path = output_manager.save_archive_data(archive_data)

    # Save summary report if requested
    if create_summary:
        output_manager.save_summary_report(archive_data, output_dir)

    return archive_path

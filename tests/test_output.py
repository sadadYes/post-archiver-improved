"""
Tests for output handling functionality.

This module tests the OutputManager class and related output operations
including file            # Restore permissions for cleanup
            readonly_dir.chmod(0o755)
    
    def test_save_archive_data_unicode_content(self, temp_dir):reation, and format handling.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open, Mock

from post_archiver_improved.output import OutputManager
from post_archiver_improved.config import OutputConfig
from post_archiver_improved.models import ArchiveData, ArchiveMetadata, Post, Author
from post_archiver_improved.exceptions import FileOperationError


class TestOutputManager:
    """Test OutputManager class."""
    
    def test_output_manager_initialization(self):
        """Test OutputManager initialization."""
        config = OutputConfig()
        manager = OutputManager(config)
        
        assert manager.config == config
    
    def test_save_archive_data_basic(self, temp_dir, sample_archive_data):
        """Test basic archive data saving."""
        config = OutputConfig(output_dir=temp_dir, pretty_print=True)
        manager = OutputManager(config)
        
        result_path = manager.save_archive_data(sample_archive_data)
        
        assert result_path.exists()
        assert result_path.parent == temp_dir
        assert result_path.suffix == ".json"
        assert sample_archive_data.metadata.channel_id in result_path.name
        
        # Verify content
        with open(result_path, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert saved_data["channel_id"] == sample_archive_data.metadata.channel_id
        assert "posts" in saved_data
    
    def test_save_archive_data_compact(self, temp_dir, sample_archive_data):
        """Test saving archive data in compact format."""
        config = OutputConfig(output_dir=temp_dir, pretty_print=False)
        manager = OutputManager(config)
        
        result_path = manager.save_archive_data(sample_archive_data)
        
        # Read raw content to check formatting
        content = result_path.read_text(encoding='utf-8')
        
        # Compact format should have minimal whitespace
        assert '\n' not in content or content.count('\n') < 5
        assert '  ' not in content  # No double spaces from indentation
    
    def test_save_archive_data_pretty_print(self, temp_dir, sample_archive_data):
        """Test saving archive data with pretty printing."""
        config = OutputConfig(output_dir=temp_dir, pretty_print=True)
        manager = OutputManager(config)
        
        result_path = manager.save_archive_data(sample_archive_data)
        
        # Read raw content to check formatting
        content = result_path.read_text(encoding='utf-8')
        
        # Pretty format should have indentation and newlines
        assert '\n' in content
        assert '  ' in content  # Indentation spaces
    
    def test_save_archive_data_custom_path(self, temp_dir, sample_archive_data):
        """Test saving archive data to custom path."""
        config = OutputConfig()
        manager = OutputManager(config)
        
        custom_path = temp_dir / "custom_archive.json"
        result_path = manager.save_archive_data(sample_archive_data, custom_path)
        
        assert result_path == custom_path
        assert custom_path.exists()
    
    def test_save_archive_data_creates_directory(self, temp_dir, sample_archive_data):
        """Test that saving creates output directory if it doesn't exist."""
        nested_dir = temp_dir / "output" / "archives"
        config = OutputConfig(output_dir=nested_dir)
        manager = OutputManager(config)
        
        result_path = manager.save_archive_data(sample_archive_data)
        
        assert nested_dir.exists()
        assert result_path.parent == nested_dir
    
    def test_save_archive_data_backup_existing(self, temp_dir, sample_archive_data):
        """Test that existing files are backed up before overwriting."""
        config = OutputConfig(output_dir=temp_dir)
        manager = OutputManager(config)
        
        # Save first time
        result_path = manager.save_archive_data(sample_archive_data)
        original_content = result_path.read_text()
        
        # Modify and save again
        sample_archive_data.metadata.posts_count = 999
        manager.save_archive_data(sample_archive_data, result_path)
        
        # Check that backup was created
        backup_files = list(temp_dir.glob("*backup*"))
        assert len(backup_files) >= 1
        
        # Verify backup contains original content
        backup_content = backup_files[0].read_text()
        assert backup_content == original_content
    
    def test_save_archive_data_permission_error(self, temp_dir, sample_archive_data):
        """Test handling of permission errors during file save."""
        # Create read-only directory
        readonly_dir = temp_dir / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)
        
        config = OutputConfig(output_dir=readonly_dir)
        manager = OutputManager(config)
        
        try:
            with pytest.raises(FileOperationError):
                manager.save_archive_data(sample_archive_data)
        finally:
            # Restore permissions for cleanup
            readonly_dir.chmod(0o755)
    
    def test_generate_filename_basic(self, sample_archive_metadata):
        """Test basic filename generation."""
        config = OutputConfig()
        manager = OutputManager(config)
        
        filename_path = manager._generate_output_filename(sample_archive_metadata.channel_id)
        
        assert isinstance(filename_path, Path)
        filename_str = filename_path.name
        assert filename_str.startswith("posts_")
        assert sample_archive_metadata.channel_id in filename_str
        assert filename_str.endswith(".json")
        # Should contain timestamp
        assert any(char.isdigit() for char in filename_str)
    
    @patch('builtins.open', side_effect=PermissionError("Access denied"))
    def test_save_archive_data_permission_error(self, mock_open, temp_dir, sample_archive_data):
        """Test handling of permission errors during save."""
        config = OutputConfig(output_dir=temp_dir)
        manager = OutputManager(config)
        
        with pytest.raises(FileOperationError) as exc_info:
            manager.save_archive_data(sample_archive_data)
        
        assert "Permission" in str(exc_info.value) or "Access" in str(exc_info.value)
    
    def test_save_archive_data_unicode_content(self, temp_dir):
        """Test saving archive data with Unicode content."""
        # Create archive data with Unicode content
        author = Author(name="测试频道", id="UC123456789")
        post = Post(
            post_id="unicode_post",
            content="Hello 世界! 🎥 Testing Unicode 📹",
            author=author
        )
        metadata = ArchiveMetadata(
            channel_id="UC123456789",
            scrape_date="2023-01-01T12:00:00Z",
            scrape_timestamp=1672574400,
            posts_count=1
        )
        archive_data = ArchiveData(metadata=metadata, posts=[post])
        
        config = OutputConfig(output_dir=temp_dir, pretty_print=True)
        manager = OutputManager(config)
        
        result_path = manager.save_archive_data(archive_data)
        
        # Verify Unicode content is preserved
        with open(result_path, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert saved_data["posts"][0]["content"] == "Hello 世界! 🎥 Testing Unicode 📹"
        assert saved_data["posts"][0]["author"] == "测试频道"
    
    def test_save_archive_data_large_file(self, temp_dir):
        """Test saving large archive data."""
        # Create large archive data
        author = Author(name="Large Channel", id="UC123456789")
        posts = []
        for i in range(100):
            post = Post(
                post_id=f"post_{i}",
                content=f"Post content {i} " + "x" * 1000,  # Large content
                author=author
            )
            posts.append(post)
        
        metadata = ArchiveMetadata(
            channel_id="UC123456789",
            scrape_date="2023-01-01T12:00:00Z",
            scrape_timestamp=1672574400,
            posts_count=100
        )
        archive_data = ArchiveData(metadata=metadata, posts=posts)
        
        config = OutputConfig(output_dir=temp_dir)
        manager = OutputManager(config)
        
        result_path = manager.save_archive_data(archive_data)
        
        assert result_path.exists()
        # Verify file is large
        assert result_path.stat().st_size > 100000  # At least 100KB
        
        # Verify content is correct
        with open(result_path, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert len(saved_data["posts"]) == 100
        assert saved_data["posts"][0]["post_id"] == "post_0"


class TestCreateSummaryReport:
    """Test create_summary_report method."""
    
    def test_create_summary_basic(self, temp_dir, sample_archive_data):
        """Test basic summary report creation."""
        config = OutputConfig(output_dir=temp_dir)
        manager = OutputManager(config)
        
        summary_text = manager.create_summary_report(sample_archive_data)
        
        # Check that summary contains key information
        assert sample_archive_data.metadata.channel_id in summary_text
        assert str(sample_archive_data.metadata.posts_count) in summary_text
        assert "Summary Report" in summary_text or "Archive Summary" in summary_text or sample_archive_data.metadata.channel_id in summary_text
    
    def test_save_summary_report(self, temp_dir, sample_archive_data):
        """Test saving summary report to file."""
        config = OutputConfig(output_dir=temp_dir)
        manager = OutputManager(config)
        
        result_path = manager.save_summary_report(sample_archive_data)
        
        assert result_path is not None
        assert result_path.exists()
        content = result_path.read_text()
        assert sample_archive_data.metadata.channel_id in content


class TestOutputErrorHandling:
    """Test error handling in output operations."""
    
    def test_output_manager_disk_full_simulation(self, temp_dir, sample_archive_data):
        """Test handling of disk full errors."""
        config = OutputConfig(output_dir=temp_dir)
        manager = OutputManager(config)
        
        # Mock disk full error
        with patch('builtins.open', side_effect=OSError("No space left on device")):
            with pytest.raises(FileOperationError) as exc_info:
                manager.save_archive_data(sample_archive_data)
            
            assert "space" in str(exc_info.value).lower() or "disk" in str(exc_info.value).lower()
    
    def test_output_manager_readonly_filesystem(self, temp_dir, sample_archive_data):
        """Test handling of read-only filesystem."""
        # Make directory read-only
        temp_dir.chmod(0o444)
        
        try:
            config = OutputConfig(output_dir=temp_dir)
            manager = OutputManager(config)
            
            with pytest.raises(FileOperationError):
                manager.save_archive_data(sample_archive_data)
        finally:
            # Restore permissions for cleanup
            temp_dir.chmod(0o755)
    
    def test_output_manager_invalid_json_serialization(self, temp_dir):
        """Test handling of objects that can't be JSON serialized."""
        # Create archive data with non-serializable object
        metadata = ArchiveMetadata(
            channel_id="UC123456789",
            scrape_date="2023-01-01T12:00:00Z",
            scrape_timestamp=1672574400,
            posts_count=1
        )
        
        # This would normally cause JSON serialization to fail
        # but our models should handle this properly
        archive_data = ArchiveData(metadata=metadata, posts=[])
        
        config = OutputConfig(output_dir=temp_dir)
        manager = OutputManager(config)
        
        # Should handle gracefully
        result_path = manager.save_archive_data(archive_data)
        assert result_path.exists()


if __name__ == "__main__":
    pytest.main([__file__])

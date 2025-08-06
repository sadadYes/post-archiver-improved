"""
Tests for configuration management functionality.

This module tests configuration loading, validation, and management
including file-based configurations and argument parsing.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from post_archiver_improved.config import (
    Config, ScrapingConfig, OutputConfig,
    get_default_config, load_config_from_file, save_config_to_file,
    load_config, update_config_from_args, get_config_search_paths
)


class TestScrapingConfig:
    """Test ScrapingConfig class."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = ScrapingConfig()
        
        assert config.max_posts == float('inf')
        assert config.extract_comments is False
        assert config.max_comments_per_post == 100
        assert config.max_replies_per_comment == 200
        assert config.download_images is False
        assert config.request_timeout == 30
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
    
    def test_custom_values(self):
        """Test configuration with custom values."""
        config = ScrapingConfig(
            max_posts=50,
            extract_comments=True,
            max_comments_per_post=25,
            download_images=True,
            request_timeout=60
        )
        
        assert config.max_posts == 50
        assert config.extract_comments is True
        assert config.max_comments_per_post == 25
        assert config.download_images is True
        assert config.request_timeout == 60


class TestOutputConfig:
    """Test OutputConfig class."""
    
    def test_default_values(self):
        """Test default output configuration values."""
        config = OutputConfig()
        
        assert config.output_dir is None
        assert config.save_format == 'json'
        assert config.pretty_print is True
        assert config.include_metadata is True
    
    def test_custom_values(self, temp_dir):
        """Test output configuration with custom values."""
        config = OutputConfig(
            output_dir=temp_dir,
            save_format='json',
            pretty_print=False,
            include_metadata=False
        )
        
        assert config.output_dir == temp_dir
        assert config.pretty_print is False
        assert config.include_metadata is False


class TestConfig:
    """Test main Config class."""
    
    def test_default_config(self):
        """Test default configuration creation."""
        config = get_default_config()
        
        assert isinstance(config.scraping, ScrapingConfig)
        assert isinstance(config.output, OutputConfig)
        assert config.log_file is None
    
    def test_post_init_path_conversion(self, temp_dir):
        """Test that paths are converted to Path objects."""
        config = Config(
            scraping=ScrapingConfig(),
            output=OutputConfig(output_dir=str(temp_dir)),
            log_file=str(temp_dir / "test.log")
        )
        
        assert isinstance(config.output.output_dir, Path)
        assert isinstance(config.log_file, Path)
        assert config.output.output_dir == temp_dir


class TestConfigFileOperations:
    """Test configuration file loading and saving."""
    
    def test_save_and_load_config(self, temp_dir):
        """Test saving and loading configuration from file."""
        config_file = temp_dir / "test_config.json"
        
        # Create a test configuration
        original_config = Config(
            scraping=ScrapingConfig(
                max_posts=25,
                extract_comments=True,
                max_comments_per_post=50
            ),
            output=OutputConfig(
                output_dir=temp_dir,
                pretty_print=False
            ),
            log_file=temp_dir / "test.log"
        )
        
        # Save configuration
        success = save_config_to_file(original_config, config_file)
        assert success is True
        assert config_file.exists()
        
        # Load configuration
        loaded_config = load_config_from_file(config_file)
        assert loaded_config is not None
        
        # Verify loaded configuration
        assert loaded_config.scraping.max_posts == 25
        assert loaded_config.scraping.extract_comments is True
        assert loaded_config.scraping.max_comments_per_post == 50
        assert loaded_config.output.pretty_print is False
        assert loaded_config.log_file == temp_dir / "test.log"
    
    def test_load_nonexistent_file(self, temp_dir):
        """Test loading configuration from non-existent file."""
        config_file = temp_dir / "nonexistent.json"
        config = load_config_from_file(config_file)
        assert config is None
    
    def test_load_invalid_json(self, temp_dir):
        """Test loading configuration from invalid JSON file."""
        config_file = temp_dir / "invalid.json"
        config_file.write_text("{ invalid json }")
        
        config = load_config_from_file(config_file)
        assert config is None
    
    def test_save_config_creates_directory(self, temp_dir):
        """Test that saving config creates parent directories."""
        nested_dir = temp_dir / "nested" / "directory"
        config_file = nested_dir / "config.json"
        
        config = get_default_config()
        success = save_config_to_file(config, config_file)
        
        assert success is True
        assert config_file.exists()
        assert nested_dir.exists()
    
    def test_infinity_handling(self, temp_dir):
        """Test handling of infinity values in configuration."""
        config_file = temp_dir / "infinity_config.json"
        
        # Create config with infinity
        config = Config(
            scraping=ScrapingConfig(max_posts=float('inf')),
            output=OutputConfig()
        )
        
        # Save and load
        save_config_to_file(config, config_file)
        loaded_config = load_config_from_file(config_file)
        
        assert loaded_config.scraping.max_posts == float('inf')
        
        # Check JSON content
        with open(config_file, 'r') as f:
            data = json.load(f)
        assert data['scraping']['max_posts'] == 'infinity'


class TestConfigLoading:
    """Test configuration loading with search paths."""
    
    def test_load_config_with_explicit_path(self, temp_dir):
        """Test loading config with explicit file path."""
        config_file = temp_dir / "explicit_config.json"
        
        # Create a test config file
        test_config = {
            "scraping": {"max_posts": 42},
            "output": {"pretty_print": False}
        }
        config_file.write_text(json.dumps(test_config))
        
        # Load config with explicit path
        config = load_config(config_file)
        assert config.scraping.max_posts == 42
        assert config.output.pretty_print is False
    
    def test_load_config_fallback_to_default(self):
        """Test loading config falls back to default when no file found."""
        config = load_config()
        
        # Should return default config
        assert isinstance(config, Config)
        assert config.scraping.max_posts == float('inf')
    
    def test_get_config_search_paths(self):
        """Test configuration search paths."""
        paths = get_config_search_paths()
        
        assert isinstance(paths, list)
        assert len(paths) > 0
        assert all(isinstance(path, Path) for path in paths)
        
        # Should include current directory
        assert any('post_archiver_config.json' in str(path) for path in paths)


class TestConfigArgumentUpdates:
    """Test updating configuration from command-line arguments."""
    
    def test_update_scraping_config(self, sample_config):
        """Test updating scraping configuration from arguments."""
        args = {
            'max_posts': 15,
            'extract_comments': True,
            'max_comments_per_post': 75,
            'download_images': True
        }
        
        updated_config = update_config_from_args(sample_config, **args)
        
        assert updated_config.scraping.max_posts == 15
        assert updated_config.scraping.extract_comments is True
        assert updated_config.scraping.max_comments_per_post == 75
        assert updated_config.scraping.download_images is True
    
    def test_update_output_config(self, sample_config, temp_dir):
        """Test updating output configuration from arguments."""
        args = {
            'output_dir': temp_dir
        }
        
        updated_config = update_config_from_args(sample_config, **args)
        
        assert updated_config.output.output_dir == temp_dir
    
    def test_update_log_file(self, sample_config, temp_dir):
        """Test updating log file from arguments."""
        log_file = temp_dir / "test.log"
        args = {
            'log_file': log_file
        }
        
        updated_config = update_config_from_args(sample_config, **args)
        
        assert updated_config.log_file == log_file
    
    def test_ignore_none_values(self, sample_config):
        """Test that None values in arguments are ignored."""
        original_max_posts = sample_config.scraping.max_posts
        
        args = {
            'max_posts': None,
            'extract_comments': True
        }
        
        updated_config = update_config_from_args(sample_config, **args)
        
        # max_posts should remain unchanged
        assert updated_config.scraping.max_posts == original_max_posts
        # extract_comments should be updated
        assert updated_config.scraping.extract_comments is True


class TestConfigEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_config_with_empty_dict(self, temp_dir):
        """Test loading config from empty JSON object."""
        config_file = temp_dir / "empty_config.json"
        config_file.write_text('{}')
        
        config = load_config_from_file(config_file)
        
        # Should create config with default values
        assert config is not None
        assert config.scraping.max_posts == float('inf')
        assert config.output.pretty_print is True
    
    def test_config_with_partial_data(self, temp_dir):
        """Test loading config with only partial data."""
        config_file = temp_dir / "partial_config.json"
        config_data = {
            "scraping": {
                "max_posts": 100
            }
            # Missing output section
        }
        config_file.write_text(json.dumps(config_data))
        
        config = load_config_from_file(config_file)
        
        assert config is not None
        assert config.scraping.max_posts == 100
        # Should use defaults for missing values
        assert config.output.pretty_print is True
    
    @patch('builtins.open', side_effect=PermissionError("Access denied"))
    def test_save_config_permission_error(self, mock_file, temp_dir):
        """Test saving config when permission is denied."""
        config_file = temp_dir / "no_permission.json"
        config = get_default_config()
        
        success = save_config_to_file(config, config_file)
        assert success is False


if __name__ == "__main__":
    pytest.main([__file__])

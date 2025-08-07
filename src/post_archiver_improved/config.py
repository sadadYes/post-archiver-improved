"""
Configuration management for the post archiver.

This module handles configuration loading, validation, and default values.
"""

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Dict, Any

from .constants import (
    DEFAULT_TIMEOUT, DEFAULT_MAX_RETRIES, DEFAULT_RETRY_DELAY,
    DEFAULT_MAX_COMMENTS, DEFAULT_MAX_REPLIES
)
from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ScrapingConfig:
    """Configuration for scraping operations."""
    max_posts: int = float('inf')
    extract_comments: bool = False
    max_comments_per_post: int = DEFAULT_MAX_COMMENTS
    max_replies_per_comment: int = DEFAULT_MAX_REPLIES
    download_images: bool = False
    request_timeout: int = DEFAULT_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES
    retry_delay: float = DEFAULT_RETRY_DELAY


@dataclass
class OutputConfig:
    """Configuration for output operations."""
    output_dir: Optional[Path] = None
    save_format: str = 'json'  # Future: support for other formats
    pretty_print: bool = True
    include_metadata: bool = True


@dataclass
class Config:
    """Main configuration container."""
    scraping: ScrapingConfig
    output: OutputConfig
    log_file: Optional[Path] = None
    
    def __post_init__(self):
        """Post-initialization processing."""
        # Ensure output_dir is a Path object
        if self.output.output_dir and not isinstance(self.output.output_dir, Path):
            self.output.output_dir = Path(self.output.output_dir)
        
        # Ensure log_file is a Path object if specified
        if self.log_file and not isinstance(self.log_file, Path):
            self.log_file = Path(self.log_file)


def get_default_config() -> Config:
    """Get default configuration."""
    return Config(
        scraping=ScrapingConfig(),
        output=OutputConfig()
    )


def load_config_from_file(config_path: Path) -> Optional[Config]:
    """
    Load configuration from a JSON file.
    
    Args:
        config_path: Path to the configuration file
    
    Returns:
        Loaded configuration or None if loading failed
    """
    try:
        if not config_path.exists():
            logger.debug(f"Config file not found: {config_path}")
            return None
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract configuration sections
        scraping_data = data.get('scraping', {})
        output_data = data.get('output', {})
        
        # Handle special cases for infinity
        if scraping_data.get('max_posts') == 'infinity' or scraping_data.get('max_posts') is None:
            scraping_data['max_posts'] = float('inf')
        
        config = Config(
            scraping=ScrapingConfig(**scraping_data),
            output=OutputConfig(**output_data),
            log_file=data.get('log_file')
        )
        
        logger.debug(f"Loaded configuration from {config_path}")
        return config
        
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.error(f"Error loading config from {config_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error loading config from {config_path}: {e}")
        return None


def save_config_to_file(config: Config, config_path: Path) -> bool:
    """
    Save configuration to a JSON file.
    
    Args:
        config: Configuration to save
        config_path: Path where to save the configuration
    
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dictionary
        data = asdict(config)
        
        # Handle special cases
        if data['scraping']['max_posts'] == float('inf'):
            data['scraping']['max_posts'] = 'infinity'
        
        # Convert Path objects to strings
        if data['output']['output_dir']:
            data['output']['output_dir'] = str(data['output']['output_dir'])
        if data['log_file']:
            data['log_file'] = str(data['log_file'])
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.debug(f"Saved configuration to {config_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving config to {config_path}: {e}")
        return False


def get_config_search_paths() -> list[Path]:
    """
    Get list of paths to search for configuration files.
    
    Returns:
        List of paths in order of precedence
    """
    paths = []
    
    # Current directory
    paths.append(Path.cwd() / 'post_archiver_config.json')
    
    # User home directory
    home_dir = Path.home()
    paths.append(home_dir / '.post_archiver_config.json')
    paths.append(home_dir / '.config' / 'post_archiver' / 'config.json')
    
    # System-wide configuration (Unix-like systems)
    if Path('/etc').exists():
        paths.append(Path('/etc') / 'post_archiver' / 'config.json')
    
    return paths


def load_config(config_path: Optional[Path] = None) -> Config:
    """
    Load configuration from file or use defaults.
    
    Args:
        config_path: Specific path to configuration file
    
    Returns:
        Loaded or default configuration
    """
    if config_path:
        config = load_config_from_file(config_path)
        if config:
            return config
        logger.warning(f"Could not load config from {config_path}, using defaults")
    else:
        # Search for config in standard locations
        for path in get_config_search_paths():
            config = load_config_from_file(path)
            if config:
                logger.info(f"Using configuration from {path}")
                return config
    
    logger.debug("Using default configuration")
    return get_default_config()


def update_config_from_args(config: Config, **kwargs) -> Config:
    """
    Update configuration with command-line arguments.
    
    Args:
        config: Base configuration to update
        **kwargs: Command-line arguments
    
    Returns:
        Updated configuration
    """
    # Update scraping config
    scraping_updates = {}
    for key in ['max_posts', 'extract_comments', 'max_comments_per_post', 
                'max_replies_per_comment', 'download_images']:
        if key in kwargs and kwargs[key] is not None:
            scraping_updates[key] = kwargs[key]
    
    if scraping_updates:
        for key, value in scraping_updates.items():
            setattr(config.scraping, key, value)
    
    # Update output config
    if 'output_dir' in kwargs and kwargs['output_dir'] is not None:
        config.output.output_dir = Path(kwargs['output_dir'])
    
    # Update log file
    if 'log_file' in kwargs and kwargs['log_file'] is not None:
        config.log_file = Path(kwargs['log_file'])
    
    return config

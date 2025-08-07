<!-- TODO: This needs to be updated due to inaccuracy. this needs to be updated to be more professional and serious -->
# Post Archiver Improved

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-GPL%20v3-blue.svg)](LICENSE)
[![Code Quality](https://img.shields.io/badge/code%20quality-A-green.svg)]()

A lightweight, zero-dependency Python tool for archiving YouTube community posts with comprehensive features including comments extraction, image downloading, and detailed logging.

This project aims to replace and improve [post-archiver](https://github.com/sadadYes/post-archiver) with better architecture, error handling, and user experience.

## ✨ Features

- **📄 Bulk archival** of YouTube community posts
- **💬 Comments extraction** with full reply chains
- **🖼️ Image downloading** with original quality preservation
- **🔧 Zero dependencies** - uses only Python standard library
- **⚡ Fast and lightweight** with intelligent rate limiting
- **📊 Detailed logging** with configurable verbosity levels
- **⚙️ Configuration management** with multiple config sources
- **📈 Progress tracking** and comprehensive error handling
- **📋 Summary reports** with detailed statistics
- **🔄 Backup creation** to prevent data loss

## 🚀 Installation

### From PyPI (Coming Soon)
```bash
pip install post-archiver-improved
```

### From Source
```bash
git clone https://github.com/sadadYes/post-archiver-improved.git
cd post-archiver-improved
pip install -e .
```

## 📖 Usage

### Basic Usage

Archive all posts from a channel:
```bash
post-archiver UC5CwaMl1eIgY8h02uZw7u8A
```

Archive with comments:
```bash
post-archiver UC5CwaMl1eIgY8h02uZw7u8A --comments
```

Archive with images:
```bash
post-archiver UC5CwaMl1eIgY8h02uZw7u8A --download-images
```

### Advanced Usage

Full archival with all features:
```bash
post-archiver UC5CwaMl1eIgY8h02uZw7u8A \
  --comments \
  --download-images \
  --max-comments 500 \
  --max-replies 100 \
  --output ./archive \
  --verbose
```

With custom configuration:
```bash
post-archiver UC5CwaMl1eIgY8h02uZw7u8A \
  --config my_config.json \
  --log-file archive.log \
  --timeout 60 \
  --retries 5
```

### Channel ID Formats

The tool accepts various channel ID formats:

- **Channel ID**: `UC5CwaMl1eIgY8h02uZw7u8A`
- **Handle**: `@username`
- **Channel URL**: `https://youtube.com/channel/UC5CwaMl1eIgY8h02uZw7u8A`
- **Custom URL**: `https://youtube.com/c/channelname`
- **Handle URL**: `https://youtube.com/@username`

## 🔧 Configuration

### Command Line Options

#### Scraping Options
- `-n, --num-posts N` - Maximum number of posts to scrape
- `-c, --comments` - Extract comments for each post
- `--max-comments N` - Maximum comments per post (default: 100)
- `--max-replies N` - Maximum replies per comment (default: 200)
- `-i, --download-images` - Download images to local directory

#### Output Options
- `-o, --output DIR` - Output directory
- `--no-summary` - Skip summary report creation
- `--compact` - Save JSON without pretty printing

#### Network Options
- `--timeout SECONDS` - Request timeout (default: 30)
- `--retries N` - Maximum retry attempts (default: 3)
- `--delay SECONDS` - Delay between requests (default: 1.0)

#### Logging Options
- `-v, --verbose` - Enable verbose output (INFO level)
- `--debug` - Enable debug output (DEBUG level)
- `--log-file FILE` - Log to file in addition to console
- `--quiet` - Suppress all output except errors

### Configuration Files

Create a configuration file for repeated use:

```json
{
  "scraping": {
    "max_posts": 100,
    "extract_comments": true,
    "max_comments_per_post": 200,
    "max_replies_per_comment": 50,
    "download_images": true,
    "request_timeout": 30,
    "max_retries": 3,
    "retry_delay": 1.0
  },
  "output": {
    "output_dir": "./archives",
    "pretty_print": true,
    "include_metadata": true
  },
  "log_file": "./logs/archiver.log"
}
```

Save current settings:
```bash
post-archiver UC5CwaMl1eIgY8h02uZw7u8A --save-config my_config.json
```

Use saved configuration:
```bash
post-archiver UC5CwaMl1eIgY8h02uZw7u8A --config my_config.json
```

## 📁 Output Format

### Archive File Structure

The tool creates a JSON file with the following structure:

```json
{
  "channel_id": "UC5CwaMl1eIgY8h02uZw7u8A",
  "scrape_date": "2025-01-15T10:30:00",
  "scrape_timestamp": 1737888600,
  "posts_count": 25,
  "total_comments": 150,
  "total_images": 10,
  "images_downloaded": 10,
  "config_used": {...},
  "posts": [
    {
      "post_id": "UgxKp7...",
      "content": "Post content here...",
      "timestamp": "2 days ago",
      "timestamp_estimated": true,
      "likes": "42",
      "comments_count": "15",
      "members_only": false,
      "author": "Channel Name",
      "author_id": "UC5CwaMl1eIgY8h02uZw7u8A",
      "author_url": "https://youtube.com/channel/...",
      "author_thumbnail": "https://...",
      "author_is_verified": true,
      "author_is_member": false,
      "images": [
        {
          "src": "https://...",
          "local_path": "./images/post_123.jpg",
          "width": 1920,
          "height": 1080,
          "file_size": 245760
        }
      ],
      "links": [
        {
          "text": "Link text",
          "url": "https://..."
        }
      ],
      "comments": [
        {
          "id": "UgwKp7...",
          "text": "Comment text...",
          "like_count": "5",
          "timestamp": "1 day ago",
          "timestamp_estimated": true,
          "author_id": "UC...",
          "author": "Commenter Name",
          "author_thumbnail": "https://...",
          "author_is_verified": false,
          "author_is_member": true,
          "author_url": "https://...",
          "is_favorited": false,
          "is_pinned": false,
          "reply_count": "2",
          "replies": [...]
        }
      ]
    }
  ]
}
```

### Files Created

- `posts_[CHANNEL_ID]_[TIMESTAMP].json` - Main archive file
- `summary_[CHANNEL_ID]_[TIMESTAMP].txt` - Summary report
- `images/` - Downloaded images (if enabled)
- `[LOG_FILE]` - Log file (if specified)

## 🛠️ Development

### Project Structure

```
src/post_archiver_improved/
├── __init__.py              # Package initialization
├── api.py                   # YouTube API client
├── cli.py                   # Command-line interface
├── comment_processor.py     # Comment extraction logic
├── config.py                # Configuration management
├── exceptions.py            # Custom exception classes
├── extractors.py            # Data extraction utilities
├── logging_config.py        # Logging configuration
├── models.py                # Data models
├── output.py                # Output handling
├── scraper.py               # Main scraper logic
└── utils.py                 # Utility functions
```

### Key Features

#### Modular Architecture
- **Separation of concerns** with dedicated modules
- **Clean interfaces** between components
- **Easy to extend** and maintain

#### Robust Error Handling
- **Custom exception hierarchy** for different error types
- **Graceful degradation** when non-critical operations fail
- **Retry logic** with exponential backoff

#### Comprehensive Logging
- **Configurable verbosity levels** (ERROR, WARNING, INFO, DEBUG)
- **Colored console output** for better readability
- **File logging** with detailed tracebacks
- **Progress tracking** with detailed statistics

#### Configuration Management
- **Multiple configuration sources** (CLI args, config files, defaults)
- **Environment-specific settings** support
- **Configuration validation** and error reporting

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=post_archiver_improved --cov-report=html
```

## 🐛 Troubleshooting

### Common Issues

#### "No community tab found"
- The channel might not have community posts enabled
- Try using the channel's full URL instead of just the ID
- Some channels restrict community tab access

#### "Rate limiting detected"
- YouTube may be limiting requests
- Increase the `--delay` parameter
- Try again later

#### "Network timeout"
- Check your internet connection
- Increase the `--timeout` parameter
- Use `--retries` to attempt multiple times

#### "Permission denied" for file operations
- Check write permissions in the output directory
- Make sure the output directory exists
- Try running with appropriate permissions

### Debug Mode

Enable debug mode for detailed troubleshooting:

```bash
post-archiver UC5CwaMl1eIgY8h02uZw7u8A --debug --log-file debug.log
```

This will provide detailed information about:
- API requests and responses
- Data extraction processes
- File operations
- Error stack traces

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

### Development Setup

1. Fork the repository
2. Clone your fork
3. Create a virtual environment
4. Install in development mode: `pip install -e ".[dev]"`
5. Make your changes
6. Run tests: `python -m pytest`
7. Submit a pull request

### Coding Standards

- Follow PEP 8 style guidelines
- Add type hints to all functions
- Write comprehensive docstrings
- Include tests for new functionality
- Update documentation as needed

## 📋 TODO

- [ ] ✅ ~~Add option to extract comments~~
- [ ] ✅ ~~Fix extracted image quality~~
- [ ] ✅ ~~Fix replies continuation logic~~
- [ ] ✅ ~~Add option to download images~~
- [ ] ✅ ~~Modularize the project to improve readability~~
- [ ] 🔄 Make this into a python package (in progress)
- [ ] 📝 Create test suites
- [ ] 📚 Create comprehensive documentation
- [ ] 🌐 Add support for other output formats (CSV, XML)
- [ ] ⚡ Add parallel processing for faster downloads
- [ ] 🔍 Add search and filtering capabilities
- [ ] 📊 Add data analysis tools

## 📄 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

This project is *heavily* inspired by the [yt-dlp community plugin](https://github.com/biggestsonicfan/yt-dlp-community-plugin) by [biggestsonicfan](https://github.com/biggestsonicfan).

## 📞 Support

If you encounter any issues or have questions:

1. Check the [troubleshooting section](#-troubleshooting)
2. Search [existing issues](https://github.com/sadadYes/post-archiver-improved/issues)
3. Create a [new issue](https://github.com/sadadYes/post-archiver-improved/issues/new) with:
   - Your command line arguments
   - Error messages or logs
   - System information (OS, Python version)
   - Expected vs actual behavior

---

⭐ **If this tool helps you, please consider giving it a star!** ⭐

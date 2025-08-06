"""
Tests for logging configuration.

This module tests logging setup, configuration, and colored output
functionality.
"""

import logging
import pytest
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch, Mock

from post_archiver_improved.logging_config import (
    ColoredFormatter, setup_logging, get_logger
)


class TestColoredFormatter:
    """Test ColoredFormatter class."""
    
    def test_formatter_creation(self):
        """Test basic formatter creation."""
        formatter = ColoredFormatter()
        assert isinstance(formatter, logging.Formatter)
    
    def test_color_constants(self):
        """Test that color constants are defined."""
        formatter = ColoredFormatter()
        
        assert hasattr(formatter, 'COLORS')
        assert hasattr(formatter, 'RESET')
        assert isinstance(formatter.COLORS, dict)
        assert isinstance(formatter.RESET, str)
        
        # Check that all log levels have colors
        expected_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        for level in expected_levels:
            assert level in formatter.COLORS
            assert isinstance(formatter.COLORS[level], str)
    
    def test_format_without_color(self):
        """Test formatting without color (non-TTY)."""
        formatter = ColoredFormatter('%(levelname)s: %(message)s')
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Mock stderr to not be a TTY
        with patch('sys.stderr') as mock_stderr:
            mock_stderr.isatty.return_value = False
            formatted = formatter.format(record)
        
        assert formatted == "INFO: Test message"
        # Should not contain ANSI color codes
        assert '\033[' not in formatted
    
    @patch('sys.stderr')
    def test_format_with_color(self, mock_stderr):
        """Test formatting with color (TTY)."""
        mock_stderr.isatty.return_value = True
        
        formatter = ColoredFormatter('%(levelname)s: %(message)s')
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Error message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        # Should contain color codes
        assert '\033[31m' in formatted  # Red for ERROR
        assert '\033[0m' in formatted   # Reset
        assert 'ERROR: Error message' in formatted
    
    def test_format_different_levels(self):
        """Test formatting for different log levels."""
        formatter = ColoredFormatter('%(levelname)s: %(message)s')
        
        test_cases = [
            (logging.DEBUG, 'DEBUG', '\033[36m'),    # Cyan
            (logging.INFO, 'INFO', '\033[32m'),      # Green
            (logging.WARNING, 'WARNING', '\033[33m'), # Yellow
            (logging.ERROR, 'ERROR', '\033[31m'),     # Red
            (logging.CRITICAL, 'CRITICAL', '\033[35m') # Magenta
        ]
        
        with patch('sys.stderr') as mock_stderr:
            mock_stderr.isatty.return_value = True
            
            for level, level_name, color_code in test_cases:
                record = logging.LogRecord(
                    name="test",
                    level=level,
                    pathname="",
                    lineno=0,
                    msg="Test message",
                    args=(),
                    exc_info=None
                )
                
                formatted = formatter.format(record)
                assert color_code in formatted
                assert level_name in formatted
                assert '\033[0m' in formatted  # Reset


class TestSetupLogging:
    """Test setup_logging function."""
    
    def teardown_method(self):
        """Clean up loggers after each test."""
        # Remove handlers from the logger to avoid interference
        logger = logging.getLogger("post_archiver_improved")
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        logger.setLevel(logging.NOTSET)
    
    def test_basic_setup(self):
        """Test basic logging setup."""
        logger = setup_logging()
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "post_archiver_improved"
        assert len(logger.handlers) > 0
    
    def test_verbose_setup(self):
        """Test verbose logging setup."""
        logger = setup_logging(verbose=True)
        
        assert logger.level == logging.INFO
    
    def test_debug_setup(self):
        """Test debug logging setup."""
        logger = setup_logging(debug=True)
        
        assert logger.level == logging.DEBUG
    
    def test_debug_overrides_verbose(self):
        """Test that debug overrides verbose setting."""
        logger = setup_logging(verbose=True, debug=True)
        
        assert logger.level == logging.DEBUG
    
    def test_default_level(self):
        """Test default logging level."""
        logger = setup_logging()
        
        # Default should be WARNING
        assert logger.level == logging.WARNING
    
    def test_file_logging(self, temp_dir):
        """Test logging to file."""
        log_file = temp_dir / "test.log"
        
        logger = setup_logging(log_file=log_file)
        
        # Should have at least two handlers: console and file
        assert len(logger.handlers) >= 2
        
        # Find file handler
        file_handler = None
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                file_handler = handler
                break
        
        assert file_handler is not None
        assert log_file.name in str(file_handler.baseFilename)
    
    def test_file_logging_creates_directory(self, temp_dir):
        """Test that file logging creates parent directories."""
        nested_dir = temp_dir / "logs" / "nested"
        log_file = nested_dir / "test.log"
        
        logger = setup_logging(log_file=log_file)
        
        # Write a test message
        logger.info("Test message")
        
        # Check that directory was created
        assert nested_dir.exists()
        assert log_file.exists()
    
    def test_console_handler_has_colored_formatter(self):
        """Test that console handler uses ColoredFormatter."""
        logger = setup_logging()
        
        # Find console handler
        console_handler = None
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stderr:
                console_handler = handler
                break
        
        assert console_handler is not None
        assert isinstance(console_handler.formatter, ColoredFormatter)
    
    def test_file_handler_has_standard_formatter(self, temp_dir):
        """Test that file handler uses standard formatter."""
        log_file = temp_dir / "test.log"
        logger = setup_logging(log_file=log_file)
        
        # Find file handler
        file_handler = None
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                file_handler = handler
                break
        
        assert file_handler is not None
        assert not isinstance(file_handler.formatter, ColoredFormatter)
        assert isinstance(file_handler.formatter, logging.Formatter)
    
    def test_custom_logger_name(self):
        """Test setup with custom logger name."""
        custom_name = "custom_logger"
        logger = setup_logging(logger_name=custom_name)
        
        assert logger.name == custom_name
    
    def test_logging_levels_work(self, temp_dir):
        """Test that different logging levels work correctly."""
        log_file = temp_dir / "levels_test.log"
        logger = setup_logging(debug=True, log_file=log_file)
        
        # Test all levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")
        
        # Check that messages were written to file
        log_content = log_file.read_text()
        assert "Debug message" in log_content
        assert "Info message" in log_content
        assert "Warning message" in log_content
        assert "Error message" in log_content
        assert "Critical message" in log_content


class TestGetLogger:
    """Test get_logger function."""
    
    def test_get_logger_basic(self):
        """Test basic logger retrieval."""
        logger = get_logger("test_module")
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"
    
    def test_get_logger_hierarchy(self):
        """Test logger hierarchy."""
        # Set up parent logger
        setup_logging(debug=True)
        
        # Get child logger
        child_logger = get_logger("post_archiver_improved.submodule")
        
        # Child should inherit parent's configuration
        assert child_logger.level == logging.DEBUG or child_logger.getEffectiveLevel() == logging.DEBUG
    
    def test_get_logger_same_instance(self):
        """Test that same logger name returns same instance."""
        logger1 = get_logger("same_name")
        logger2 = get_logger("same_name")
        
        assert logger1 is logger2


class TestLoggingIntegration:
    """Test logging integration with the application."""
    
    def teardown_method(self):
        """Clean up loggers after each test."""
        # Remove handlers from the logger to avoid interference
        logger = logging.getLogger("post_archiver_improved")
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        logger.setLevel(logging.NOTSET)
    
    def test_module_logger_names(self):
        """Test that module loggers have correct names."""
        # This would be called from within modules
        api_logger = get_logger("post_archiver_improved.api")
        config_logger = get_logger("post_archiver_improved.config")
        
        assert api_logger.name == "post_archiver_improved.api"
        assert config_logger.name == "post_archiver_improved.config"
    
    def test_logging_with_file_permissions_error(self, temp_dir):
        """Test handling of file permission errors."""
        # Create a read-only directory
        readonly_dir = temp_dir / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)  # Read-only
        
        log_file = readonly_dir / "test.log"
        
        # This should not raise an exception
        try:
            logger = setup_logging(log_file=log_file)
            # Should fall back to console-only logging
            assert len(logger.handlers) >= 1
        except Exception as e:
            pytest.fail(f"setup_logging should handle permission errors gracefully: {e}")
        finally:
            # Clean up - restore permissions
            readonly_dir.chmod(0o755)
    
    def test_log_message_format(self, temp_dir):
        """Test that log messages have expected format."""
        log_file = temp_dir / "format_test.log"
        logger = setup_logging(debug=True, log_file=log_file)
        
        test_message = "Test log message"
        logger.info(test_message)
        
        log_content = log_file.read_text()
        
        # Should contain timestamp, level, and message
        assert test_message in log_content
        assert "INFO" in log_content
        # Should have timestamp (basic check for date-like format)
        assert any(char.isdigit() for char in log_content)
    
    def test_exception_logging(self, temp_dir):
        """Test logging of exceptions with tracebacks."""
        log_file = temp_dir / "exception_test.log"
        logger = setup_logging(debug=True, log_file=log_file)
        
        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.exception("An error occurred")
        
        log_content = log_file.read_text()
        
        # Should contain exception message and traceback
        assert "An error occurred" in log_content
        assert "ValueError" in log_content
        assert "Test exception" in log_content
        assert "Traceback" in log_content


class TestLoggingConfiguration:
    """Test various logging configurations."""
    
    def teardown_method(self):
        """Clean up loggers after each test."""
        logger = logging.getLogger("post_archiver_improved")
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        logger.setLevel(logging.NOTSET)
    
    def test_multiple_setup_calls(self):
        """Test that multiple setup calls don't create duplicate handlers."""
        logger1 = setup_logging(verbose=True)
        initial_handler_count = len(logger1.handlers)
        
        logger2 = setup_logging(debug=True)
        
        # Should not have duplicate handlers
        assert len(logger2.handlers) <= initial_handler_count + 1  # Allow for potential file handler
    
    def test_quiet_mode_simulation(self):
        """Test configuration that simulates quiet mode."""
        # Capture output by mocking stderr before logger setup
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            # Simulate quiet mode by setting high level
            logger = setup_logging()
            logger.setLevel(logging.ERROR)
            
            logger.info("This should not appear")
            logger.warning("This should not appear")
            logger.error("This should appear")
            
            output = mock_stderr.getvalue()
            
            assert "This should not appear" not in output
            assert "This should appear" in output


if __name__ == "__main__":
    pytest.main([__file__])

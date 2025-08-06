"""
Basic tests for the post archiver package.

This module contains basic sanity tests to ensure the package
can be imported and basic functionality works.
"""

import pytest
import sys
from pathlib import Path

# Ensure we can import the package
def test_package_import():
    """Test that the package can be imported successfully."""
    try:
        import post_archiver_improved
        assert hasattr(post_archiver_improved, '__version__')
        assert hasattr(post_archiver_improved, '__author__')
        assert hasattr(post_archiver_improved, '__description__')
    except ImportError as e:
        pytest.fail(f"Failed to import package: {e}")


def test_version_string():
    """Test that version string is valid."""
    import post_archiver_improved
    version = post_archiver_improved.__version__
    
    assert isinstance(version, str)
    assert len(version) > 0
    # Basic version format check (e.g., "0.1.0")
    assert '.' in version


def test_module_imports():
    """Test that all main modules can be imported."""
    modules_to_test = [
        'post_archiver_improved.api',
        'post_archiver_improved.cli',
        'post_archiver_improved.config',
        'post_archiver_improved.exceptions',
        'post_archiver_improved.extractors',
        'post_archiver_improved.logging_config',
        'post_archiver_improved.models',
        'post_archiver_improved.output',
        'post_archiver_improved.scraper',
        'post_archiver_improved.utils',
        'post_archiver_improved.comment_processor'
    ]
    
    for module_name in modules_to_test:
        try:
            __import__(module_name)
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")


def test_python_version():
    """Test that Python version meets requirements."""
    assert sys.version_info >= (3, 8), "Python 3.8+ is required"


def test_package_structure():
    """Test that package has expected structure."""
    import post_archiver_improved
    package_dir = Path(post_archiver_improved.__file__).parent
    
    expected_files = [
        '__init__.py',
        'api.py',
        'cli.py',
        'config.py',
        'exceptions.py',
        'extractors.py',
        'logging_config.py',
        'models.py',
        'output.py',
        'scraper.py',
        'utils.py',
        'comment_processor.py'
    ]
    
    for file_name in expected_files:
        file_path = package_dir / file_name
        assert file_path.exists(), f"Expected file {file_name} not found"
        assert file_path.is_file(), f"{file_name} is not a file"


def test_entry_point_exists():
    """Test that CLI entry point can be imported."""
    try:
        from post_archiver_improved.cli import main
        assert callable(main)
    except ImportError as e:
        pytest.fail(f"Failed to import CLI main function: {e}")


class TestPackageMetadata:
    """Test package metadata and constants."""
    
    def test_author_info(self):
        """Test author information is present."""
        import post_archiver_improved
        assert post_archiver_improved.__author__ == "sadadYes"
    
    def test_description_info(self):
        """Test description is present and meaningful."""
        import post_archiver_improved
        description = post_archiver_improved.__description__
        assert isinstance(description, str)
        assert len(description) > 10
        assert "youtube" in description.lower() or "post" in description.lower()
    
    def test_version_format(self):
        """Test version follows semantic versioning."""
        import post_archiver_improved
        version = post_archiver_improved.__version__
        
        # Basic semantic versioning check (X.Y.Z)
        parts = version.split('.')
        assert len(parts) >= 2, "Version should have at least major.minor"
        
        for part in parts[:3]:  # Check first 3 parts if they exist
            assert part.isdigit() or '-' in part, f"Version part '{part}' should be numeric or contain dash for pre-release"


if __name__ == "__main__":
    pytest.main([__file__])

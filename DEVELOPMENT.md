# Development Setup Guide

This guide helps you set up the development environment for Post Archiver Improved.

## Quick Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/sadadYes/post-archiver-improved.git
   cd post-archiver-improved
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install in development mode with all dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

## Versioning

The package uses dynamic versioning from `src/post_archiver_improved/__init__.py`. To update the version:

1. Edit `src/post_archiver_improved/__init__.py`
2. Update the `__version__` variable
3. The version will automatically be used in `pyproject.toml` during build

## Building the Package

```bash
# Build both source distribution and wheel
python -m build

# Files will be created in dist/
# - post_archiver_improved-{version}.tar.gz (source)
# - post_archiver_improved-{version}-py3-none-any.whl (wheel)
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=post_archiver_improved --cov-report=html

# Run specific test file
pytest tests/test_basic.py -v
```

## Code Quality Tools

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Type checking
mypy src/

# Linting
flake8 src/ tests/
pylint src/post_archiver_improved/
```

## Installation Options

### For Users
```bash
pip install post-archiver-improved
```

### For Development
```bash
pip install -e ".[dev]"  # All development tools
pip install -e ".[test]" # Only testing tools
pip install -e ".[docs]" # Only documentation tools
```

## Publishing (Maintainers Only)

1. **Update version** in `src/post_archiver_improved/__init__.py`
2. **Update CHANGELOG.md** with new version details
3. **Build package:**
   ```bash
   python -m build
   ```
4. **Upload to PyPI:**
   ```bash
   twine upload dist/*
   ```

## File Structure

```
post-archiver-improved/
├── src/post_archiver_improved/    # Main package code
├── tests/                         # Test suite
├── dist/                         # Built packages (created by build)
├── pyproject.toml                # Project configuration
├── README.md                     # Main documentation
├── CHANGELOG.md                  # Version history
├── CONTRIBUTING.md               # Contribution guidelines
├── LICENSE                       # License file
└── MANIFEST.in                   # Package manifest
```

## Key Features

- **Zero Dependencies**: Main package has no external dependencies
- **Dynamic Versioning**: Version managed in single location
- **Modern Configuration**: Uses pyproject.toml for all configuration
- **Type Support**: Includes py.typed marker for type hints
- **Development Tools**: Pre-configured black, isort, mypy, pytest
- **Professional Structure**: Follows Python packaging best practices

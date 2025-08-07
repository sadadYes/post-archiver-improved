# Contributing to Post Archiver Improved

Thank you for your interest in contributing to Post Archiver Improved! This document provides guidelines and information for contributors.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. Please be respectful and constructive in all interactions.

## How to Contribute

### Reporting Issues

Before creating an issue, please:

1. **Search existing issues** to see if your problem has already been reported
2. **Use the latest version** to ensure the issue still exists
3. **Provide detailed information** including:
   - Operating system and version
   - Python version
   - Complete error messages and stack traces
   - Steps to reproduce the issue
   - Expected vs actual behavior

### Suggesting Features

When suggesting new features:

1. **Check existing feature requests** to avoid duplicates
2. **Explain the use case** and why the feature would be valuable
3. **Provide examples** of how the feature would work
4. **Consider the scope** - features should align with the project's goals

### Contributing Code

#### Development Setup

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/post-archiver-improved.git
   cd post-archiver-improved
   ```

3. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install in development mode**:
   ```bash
   pip install -e ".[dev]"
   ```

5. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

#### Development Guidelines

**Code Style:**
- Follow PEP 8 style guidelines
- Use Ruff for code formatting and linting: `ruff format src/ tests/` and `ruff check src/ tests/`
- Line length limit: 88 characters

**Type Hints:**
- Add type hints to all functions and methods
- Use `from typing import` for type annotations
- Ensure mypy passes: `mypy src/`

**Documentation:**
- Write comprehensive docstrings for all functions and classes
- Use Google or NumPy docstring format
- Update README.md if adding new features
- Add inline comments for complex logic

**Testing:**
- Write tests for all new functionality
- Maintain or improve test coverage
- Use pytest for testing: `pytest tests/`
- Run tests with coverage: `pytest tests/ --cov=post_archiver_improved`

**Error Handling:**
- Use appropriate custom exceptions from `exceptions.py`
- Provide meaningful error messages
- Handle edge cases gracefully
- Log errors appropriately

#### Commit Guidelines (I don't really care about this, just be coherent (optional))

**Commit Messages:**
- Use clear, descriptive commit messages
- Start with a verb in present tense (Add, Fix, Update, etc.)
- Keep the first line under 50 characters
- Add detailed description if necessary

**Examples:**
```
Add support for playlist archiving

- Implement playlist detection logic
- Add configuration options for playlist handling
- Update CLI to accept playlist URLs
- Add comprehensive tests for playlist functionality
```

#### Pull Request Process

1. **Ensure all tests pass**:
   ```bash
   pytest tests/
   mypy src/
   ruff check src/ tests/
   ruff format --check src/ tests/
   ```

2. **Update documentation** if necessary

3. **Create a pull request** with:
   - Clear title describing the change
   - Detailed description of what was changed and why
   - Reference to any related issues
   - Screenshots or examples if applicable

4. **Respond to review feedback** promptly and professionally

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=post_archiver_improved --cov-report=html

# Run specific test file
pytest tests/test_scraper.py

# Run with verbose output
pytest tests/ -v
```

### Code Quality Checks

```bash
# Format and lint code
ruff format src/ tests/
ruff check src/ tests/

# Type checking
mypy src/
```

### Building and Testing Package

```bash
# Build package
python -m build

# Test installation
pip install dist/post_archiver_improved-*.whl

# Test package
post-archiver --help
```

## Project Structure

```
post-archiver-improved/
├── src/post_archiver_improved/    # Main package code
│   ├── __init__.py               # Package initialization
│   ├── api.py                    # YouTube API client
│   ├── cli.py                    # Command-line interface
│   ├── comment_processor.py      # Comment extraction
│   ├── config.py                 # Configuration management
│   ├── constants.py              # Application constants
│   ├── exceptions.py             # Custom exceptions
│   ├── extractors.py             # Data extractors
│   ├── logging_config.py         # Logging setup
│   ├── models.py                 # Data models
│   ├── output.py                 # Output handling
│   ├── scraper.py                # Main scraper logic
│   └── utils.py                  # Utility functions
├── tests/                        # Test suite
├── docs/                         # Documentation
├── pyproject.toml                # Project configuration
├── README.md                     # Project documentation
├── CHANGELOG.md                  # Version history
├── CONTRIBUTING.md               # This file
├── LICENSE                       # Project license
└── MANIFEST.in                   # Package manifest
```

## Design Principles

- **Zero Dependencies**: The main package should not depend on external libraries
- **Modular Design**: Keep components separate and focused
- **Error Resilience**: Handle failures gracefully
- **Performance**: Optimize for speed and memory usage
- **Usability**: Provide clear, helpful interfaces
- **Extensibility**: Design for future enhancements

## Getting Help

If you need help with development:

1. **Check the documentation** in the README and docstrings
2. **Look at existing code** for examples and patterns
3. **Ask questions** in GitHub issues or discussions
4. **Join the community** and engage with other contributors

## Recognition

Contributors will be recognized in:
- The project's contributor list
- My heart ;)

Thank you for contributing to Post Archiver Improved!

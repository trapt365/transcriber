# Contributing to Transcriber

Thank you for your interest in contributing to Transcriber! This document provides guidelines and information for contributors.

## Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/yourusername/transcriber.git
   cd transcriber
   ```

2. **Set up development environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements-dev.txt
   ```

3. **Install pre-commit hooks**
   ```bash
   pre-commit install
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your test credentials
   ```

## Code Standards

### Python Style Guide

- Follow PEP 8 (enforced by black and flake8)
- Use type hints for all functions
- Write docstrings for all public functions and classes
- Maximum line length: 88 characters

### Code Formatting

```bash
# Format code before committing
black backend/ tests/

# Check linting
flake8 backend/ tests/

# Type checking
mypy backend/
```

### Testing Requirements

- Write unit tests for all new functionality
- Maintain test coverage above 80%
- Use pytest fixtures for test data
- Separate unit and integration tests

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html
```

## Contribution Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write code following our standards
   - Add tests for new functionality
   - Update documentation if needed

3. **Test your changes**
   ```bash
   # Run all tests
   pytest

   # Run pre-commit checks
   pre-commit run --all-files
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push and create Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```

## Commit Message Convention

Use conventional commits format:

- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `style:` Code style changes
- `refactor:` Code refactoring
- `test:` Test additions or modifications
- `chore:` Build process or auxiliary tool changes

Example: `feat: add real-time transcription status updates`

## Pull Request Guidelines

### Before Submitting

- [ ] All tests pass
- [ ] Code coverage is maintained
- [ ] Pre-commit hooks pass
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated (if applicable)

### PR Description Template

```markdown
## Description
Brief description of the changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests added/updated
- [ ] All tests passing
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project standards
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

## Issue Reporting

### Bug Reports

Include:
- Environment details (OS, Python version, etc.)
- Steps to reproduce
- Expected vs actual behavior
- Error messages/logs
- Screenshots if applicable

### Feature Requests

Include:
- Use case description
- Proposed solution
- Alternative solutions considered
- Additional context

## Development Guidelines

### Database Changes

1. Create migrations for schema changes
   ```bash
   flask db migrate -m "Description of change"
   ```

2. Test migrations in both directions
   ```bash
   flask db upgrade
   flask db downgrade
   ```

### API Changes

1. Update API documentation
2. Ensure backward compatibility
3. Add integration tests
4. Update OpenAPI spec if applicable

### Frontend Changes

1. Test in multiple browsers
2. Ensure responsive design
3. Update UI tests
4. Follow accessibility guidelines

## Release Process

1. **Version Bumping**
   - Update version in `pyproject.toml`
   - Update CHANGELOG.md
   - Create version tag

2. **Testing**
   - Run full test suite
   - Test Docker builds
   - Verify deployment process

3. **Documentation**
   - Update API documentation
   - Update README if needed
   - Review deployment docs

## Community Guidelines

### Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow
- Report inappropriate behavior

### Getting Help

- Check existing issues and documentation
- Ask questions in GitHub Discussions
- Be specific about your problem
- Include relevant context and code samples

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Annual contributor highlights

Thank you for contributing to Transcriber! 🎉
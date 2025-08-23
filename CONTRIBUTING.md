# Contributing to NetBox Component Synchronization

Thank you for your interest in contributing to this project! This guide will help you get started with development and testing.

## Development Environment Setup

### Prerequisites

- Python 3.9+
- NetBox 4.0+ (for full testing)
- Git

### Setting Up for Development

1. Fork and clone the repository:
```bash
git clone https://github.com/your-username/netbox-component-synchronization.git
cd netbox-component-synchronization
```

2. Install development dependencies:
```bash
pip install -e .
pip install -r .github/test-requirements.txt
```

3. Run tests to verify setup:
```bash
python run_tests.py --test-type validation
```

## Testing Framework

### Universal Testing Approach

This project uses a universal testing framework that works across different environments:

- **Full NetBox Environment**: Complete integration testing with Django and NetBox models
- **Django-Only Environment**: Core functionality testing without NetBox models  
- **Minimal Environment**: Basic validation testing without Django

### Running Tests

```bash
# Run all available tests
python run_tests.py

# Run only validation tests (works everywhere)
python run_tests.py --test-type validation

# Run unit tests only
python run_tests.py --test-type unit

# Run with pytest (if available)
python run_tests.py --pytest --verbose
```

### Test Structure

```
tests/
├── __init__.py              # Test package initialization
├── base.py                  # Universal base test classes
├── test_component_registry.py # Component registry tests
├── test_async_utils.py      # Async utilities tests  
├── test_validation.py       # Basic validation tests
└── test_refactoring_universal.py # Refactored functionality tests
```

### Writing Tests

Use the universal base classes for new tests:

```python
from tests.base import BaseUniversalTestCase, ValidationTestMixin

class MyNewTests(BaseUniversalTestCase, ValidationTestMixin):
    def test_my_feature(self):
        """Test my new feature."""
        try:
            from netbox_component_synchronization import my_module
            # Test with full NetBox environment
            self.assert_module_importable('my_module')
        except ImportError:
            self.skipTest("NetBox not available")
```

## Code Quality

### Formatting

This project uses automated code formatting:

- **Black**: Code formatting
- **isort**: Import sorting  
- **flake8**: Linting

Format your code before committing:
```bash
black .
isort .
flake8 .
```

### Pre-commit Setup

Install pre-commit hooks (recommended):
```bash
pip install pre-commit
pre-commit install
```

## Continuous Integration

### Automated Workflows

The project includes several GitHub Actions workflows:

1. **PR Testing** (`.github/workflows/test-pr.yml`)
   - Tests against multiple NetBox versions
   - Runs on all pull requests

2. **Code Formatting** (`.github/workflows/format-code.yml`)  
   - Checks code formatting
   - Auto-formats code on main branch

3. **NetBox Release Monitoring** (`.github/workflows/check-netbox-releases.yml`)
   - Daily check for new NetBox versions
   - Creates issues and triggers compatibility tests

4. **Compatibility Testing** (`.github/workflows/test-netbox-compatibility.yml`)
   - Tests against specific NetBox versions
   - Creates PRs for compatibility updates

### Adding New NetBox Version Support

When a new NetBox version is released:

1. The monitoring workflow automatically detects it
2. A compatibility issue is created
3. Tests run against the new version
4. If tests pass, a PR is automatically created

Manual testing against a specific version:
```bash
# Trigger compatibility workflow manually
# (Requires repository write access)
```

## Contribution Workflow

### Making Changes

1. Create a feature branch:
```bash
git checkout -b feature/my-new-feature
```

2. Make your changes and add tests
3. Run tests locally:
```bash
python run_tests.py
```

4. Commit with descriptive messages:
```bash
git commit -m "Add new component type support"
```

5. Push and create a pull request

### Pull Request Guidelines

- Include tests for new functionality
- Update documentation if needed
- Ensure all CI checks pass
- Write clear commit messages
- Reference any related issues

### Code Review Process

1. Automated tests run on all PRs
2. Code formatting is checked/applied automatically
3. Maintainers review the changes
4. Address any feedback
5. Merge after approval

## NetBox Version Compatibility

### Supported Versions

- NetBox 4.0+
- Python 3.9+

### Version Testing Matrix

The CI system tests against:
- NetBox 4.0 (LTS)
- NetBox 4.1  
- NetBox latest release
- Python 3.9, 3.10, 3.11

### Adding Support for New Components

1. Add component configuration to `component_registry.py`
2. Add comparison class to `comparison.py` if needed
3. Write universal tests
4. Update documentation

Example:
```python
# In component_registry.py
'mynewcomponent': ComponentConfig(
    component_label="My New Components",
    model=MyNewComponent,
    template_model=MyNewComponentTemplate,
    comparison_class=MyNewComponentComparison,
    permissions=("dcim.view_mynewcomponent", ...),
    factory_fields=('id', 'name', 'type'),
)
```

## Getting Help

- Create an issue for bugs or feature requests
- Check existing issues and discussions
- Review the test output for debugging information

## Release Process

Releases are managed by maintainers:

1. Version bump in `setup.py`
2. Update changelog
3. Create release tag
4. Automated publishing to PyPI

Thank you for contributing!
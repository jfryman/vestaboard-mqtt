# Vestaboard MQTT Bridge - Test Suite

This directory contains the test suite for the Vestaboard MQTT Bridge project.

## Setup

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run with coverage report
```bash
pytest --cov=src --cov-report=html
```

### Run specific test file
```bash
pytest tests/test_board_types.py
pytest tests/test_vestaboard_client.py
pytest tests/test_env_board_type.py
```

### Run specific test class or function
```bash
# Run specific class
pytest tests/test_board_types.py::TestBoardTypeConstants

# Run specific test
pytest tests/test_board_types.py::TestBoardTypeConstants::test_standard_board_dimensions
```

### Run tests with verbose output
```bash
pytest -v
```

### Run tests and show print statements
```bash
pytest -s
```

## Test Organization

### `test_board_types.py`
Tests for board type constants and utility functions:
- `BoardType` constant definitions (STANDARD, NOTE)
- Character code mappings (CHAR_CODE_MAP, TEXT_TO_CODE_MAP)
- `text_to_layout()` function for converting text to layout arrays
- `debug_layout_preview()` function for logging layouts
- Parametrized tests for various board dimensions

### `test_vestaboard_client.py`
Tests for client initialization and board type integration:
- `VestaboardClient` initialization with different board types
- `LocalVestaboardClient` initialization with different board types
- Factory function (`create_vestaboard_client()`) behavior
- Board type propagation through client operations
- API key handling and validation
- Client interface compliance with `BaseVestaboardClient`

### `test_env_board_type.py`
Tests for environment variable parsing:
- `VESTABOARD_BOARD_TYPE` parsing (standard, note, custom)
- Case-insensitive handling (STANDARD, standard, NOTE, note)
- Custom dimension parsing (e.g., "3,15", "4,20")
- Parameter override behavior (explicit parameter overrides env var)
- Invalid value handling and error messages
- Integration with Local API and Cloud API modes
- Parametrized tests for various valid and invalid values

## Coverage Reports

After running tests with coverage, view the HTML report:

```bash
# Generate coverage report
pytest --cov=src --cov-report=html

# Open in browser (macOS)
open htmlcov/index.html

# Open in browser (Linux)
xdg-open htmlcov/index.html
```

## CI/CD Integration

These tests are designed to run in CI/CD pipelines. Example GitHub Actions workflow:

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r requirements-dev.txt
      - run: pytest --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v2
```

## Writing New Tests

When adding new functionality:

1. **Create test file** following naming convention: `test_<module_name>.py`
2. **Organize tests** into classes by feature area
3. **Use descriptive names**: `test_<what_is_being_tested>`
4. **Add docstrings**: Explain what the test verifies
5. **Use parametrize**: For testing multiple similar scenarios
6. **Use fixtures**: For common setup/teardown (see pytest docs)
7. **Mark tests**: Use `@pytest.mark.unit` or `@pytest.mark.integration`

Example:

```python
import pytest
from src.my_module import my_function

class TestMyFunction:
    """Tests for my_function."""

    def test_basic_functionality(self):
        """Test basic functionality of my_function."""
        result = my_function("input")
        assert result == "expected_output"

    @pytest.mark.parametrize("input_val,expected", [
        ("a", "A"),
        ("b", "B"),
    ])
    def test_multiple_inputs(self, input_val, expected):
        """Test my_function with various inputs."""
        assert my_function(input_val) == expected
```

## Test Markers

Available test markers (defined in `pytest.ini`):

- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (may require external services)

Run only unit tests:
```bash
pytest -m unit
```

Run only integration tests:
```bash
pytest -m integration
```

## Troubleshooting

### Import Errors
If you get import errors, make sure you're running pytest from the project root:
```bash
# From project root
pytest tests/

# Not from tests/ directory
```

### Module Not Found
Ensure you've installed development dependencies:
```bash
pip install -r requirements-dev.txt
```

### Coverage Not Working
Make sure pytest-cov is installed:
```bash
pip install pytest-cov
```

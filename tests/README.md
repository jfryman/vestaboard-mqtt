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

### Unit Tests

#### `test_board_types.py`
Tests for board type constants and utility functions:
- `BoardType` constant definitions (STANDARD, NOTE)
- Character code mappings (CHAR_CODE_MAP, TEXT_TO_CODE_MAP)
- `text_to_layout()` function for converting text to layout arrays
- `debug_layout_preview()` function for logging layouts
- Parametrized tests for various board dimensions

#### `test_vestaboard_client.py`
Tests for client initialization and board type integration:
- `VestaboardClient` initialization with different board types
- `LocalVestaboardClient` initialization with different board types
- Factory function (`create_vestaboard_client()`) behavior
- Board type propagation through client operations
- API key handling and validation
- Client interface compliance with `BaseVestaboardClient`

#### `test_env_board_type.py`
Tests for environment variable parsing:
- `VESTABOARD_BOARD_TYPE` parsing (standard, note, custom)
- Case-insensitive handling (STANDARD, standard, NOTE, note)
- Custom dimension parsing (e.g., "3,15", "4,20")
- Parameter override behavior (explicit parameter overrides env var)
- Invalid value handling and error messages
- Integration with Local API and Cloud API modes
- Parametrized tests for various valid and invalid values

#### `test_mqtt_bridge.py`
Comprehensive tests for VestaboardMQTTBridge (75+ tests):
- Initialization with various MQTT configurations
- TLS/SSL configuration (basic, mutual TLS, insecure mode)
- Last Will and Testament (LWT) configuration
- Topic prefix handling and multi-Vestaboard support
- MQTT callbacks (connect, disconnect, message)
- Message handling (text, JSON layouts, JSON objects)
- Save/restore/delete operations
- Timed message scheduling and management
- Timer cancellation and listing
- Cleanup on stop

#### `test_save_state_manager.py`
Tests for SaveStateManager (30+ tests):
- Initialization and topic prefix configuration
- Saving current state to MQTT retained messages
- Restoring from saved state data
- Handling different layout formats (array, JSON string, message wrapper)
- Delete operations
- Error handling and edge cases
- JSON serialization and validation
- Parametrized tests for various data formats

#### `test_http_api.py`
Tests for HTTP API endpoints (25+ tests):
- VestaboardHTTPAPI initialization
- Health endpoint (`/health`) for liveness probes
- Readiness endpoint (`/ready`) for readiness probes
- Metrics endpoint (`/metrics`) for monitoring
- Kubernetes probe compatibility
- Concurrent request handling
- OpenAPI schema validation
- Parametrized endpoint structure tests

#### `test_main.py`
Tests for configuration loading and application entry point (40+ tests):
- Basic configuration defaults
- MQTT broker configuration
- Topic prefix configuration
- Advanced MQTT settings (client ID, clean session, keepalive, QoS)
- TLS/SSL configuration (basic, mutual TLS, insecure mode)
- Last Will and Testament configuration
- Vestaboard API key configuration (cloud, local, precedence)
- HTTP server configuration
- Message queue configuration
- Boolean environment variable parsing
- Complete configuration integration
- Configuration structure and type validation
- Parametrized tests for defaults and boolean parsing

### Integration Tests

#### `test_integration.py`
End-to-end integration tests (20+ tests):
- Complete message flow from MQTT to Vestaboard
- Save and restore workflows
- Timed message workflows with auto-restore
- Multi-Vestaboard deployment scenarios
- HTTP API integration with MQTT bridge
- Error recovery and graceful degradation
- Malformed data handling
- Complete real-world workflows
- Performance and load testing
- Concurrent request handling

## Test Statistics

The test suite includes:
- **200+ total tests** across 8 test files
- **Unit tests**: Tests for individual components and functions
- **Integration tests**: End-to-end workflow testing
- **Parametrized tests**: Efficient testing of multiple scenarios
- **Comprehensive coverage**: All major functionality is tested

Test breakdown by file:
- `test_board_types.py`: 20+ tests
- `test_vestaboard_client.py`: 40+ tests
- `test_env_board_type.py`: 25+ tests
- `test_mqtt_bridge.py`: 75+ tests
- `test_save_state_manager.py`: 30+ tests
- `test_http_api.py`: 25+ tests
- `test_main.py`: 40+ tests
- `test_integration.py`: 20+ tests

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

- `@pytest.mark.unit` - Unit tests for individual components (fast, isolated)
- `@pytest.mark.integration` - Integration tests across multiple components
- `@pytest.mark.slow` - Tests that take longer to run
- `@pytest.mark.mqtt` - Tests related to MQTT functionality
- `@pytest.mark.api` - Tests related to HTTP API
- `@pytest.mark.config` - Tests related to configuration

Run only unit tests:
```bash
pytest -m unit
```

Run only integration tests:
```bash
pytest -m integration
```

Run all tests except slow ones:
```bash
pytest -m "not slow"
```

Run only MQTT-related tests:
```bash
pytest -m mqtt
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

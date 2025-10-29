# Vestaboard MQTT Bridge - Project Context

## Overview
This project is a Python application that bridges MQTT messages to Vestaboard displays via the Read/Write API. It provides persistent save states, timed messages with auto-restore, and comprehensive monitoring capabilities.

## Quick Links
- **User Documentation:** [README.md](README.md) - Features, quick start, configuration
- **API Specification:** [INTERFACE_SPEC.md](INTERFACE_SPEC.md) - Complete MQTT/HTTP API reference
- **Development Guide:** [DEVELOPMENT.md](DEVELOPMENT.md) - Developer workflow and tooling
- **Testing Guide:** [tests/README.md](tests/README.md) - Test suite documentation

## Project Structure
```
├── src/
│   ├── main.py                 # Application entry point
│   ├── config.py              # Pydantic configuration models
│   ├── logger.py              # Logging configuration
│   ├── http_api.py            # FastAPI health/metrics endpoints
│   ├── mqtt/
│   │   ├── bridge.py          # Core MQTT bridge
│   │   ├── handlers.py        # Message handlers
│   │   ├── timers.py          # Timed message management
│   │   └── topics.py          # Topic constants
│   ├── state/
│   │   └── manager.py         # State persistence via MQTT
│   └── vestaboard/
│       ├── base.py            # Abstract base client
│       ├── cloud_client.py    # Cloud API client
│       ├── local_client.py    # Local API client
│       ├── factory.py         # Client factory
│       ├── board_types.py     # Board type constants
│       ├── utils.py           # Utility functions
│       └── constants.py       # Character code mappings
├── tests/                     # Comprehensive test suite (200+ tests)
├── helpers/                   # Testing and monitoring scripts
├── scripts/                   # Code quality and development scripts
└── deploy/                    # Docker and Kubernetes deployment
```

## Architecture

### Key Classes

**VestaboardMQTTBridge** (`src/mqtt/bridge.py`)
- Main MQTT client handling all message routing
- Configures MQTT connection with TLS/SSL and LWT support
- Manages topic subscriptions and message routing
- Coordinates between handlers, timers, and state manager

**MessageHandlers** (`src/mqtt/handlers.py`)
- Handles incoming MQTT messages
- Routes to appropriate operations (message, save, restore, timed, etc.)
- Parses payloads and validates input

**TimerManager** (`src/mqtt/timers.py`)
- Manages timed messages with auto-restore
- Uses Python `threading.Timer` for scheduling
- Handles rate limiting between timed message and restore
- Tracks active timers for cancellation

**SaveStateManager** (`src/state/manager.py`)
- Manages save/restore via MQTT retained messages
- JSON serialization of display states
- Reads current state from Vestaboard API
- Compatible with both Cloud and Local API clients

**VestaboardClient & LocalVestaboardClient** (`src/vestaboard/`)
- **Cloud API:** `cloud_client.py` - Cloud Read/Write API
- **Local API:** `local_client.py` - Local API support
- **Base Client:** `base.py` - Abstract interface
- **Factory:** `factory.py` - Automatic client selection
- **Rate Limiting:** Shared via RateLimitMixin (DRY principle)
- **Board Types:** Supports Standard (6x22) and Note (3x15)

**HTTP API** (`src/http_api.py`)
- FastAPI server for health checks and metrics
- Endpoints: `/health`, `/ready`, `/metrics`
- Kubernetes-ready liveness/readiness probes

**Configuration** (`src/config.py`)
- Pydantic models for type-safe configuration
- Environment variable parsing
- TLS/SSL and LWT configuration models

## Core Functionality

### MQTT Topics
See [INTERFACE_SPEC.md](INTERFACE_SPEC.md#mqtt-interface) for complete MQTT topic documentation.

### Environment Variables
See [README.md](README.md#configuration) for configuration options and [INTERFACE_SPEC.md](INTERFACE_SPEC.md#configuration) for formal specification.

### Multi-Vestaboard Support
Configure unique topic prefixes per instance using `MQTT_TOPIC_PREFIX` to control multiple Vestaboards independently (e.g., `office-board`, `lobby-board`).

### Board Type Support
- **Standard Vestaboard:** 6 rows × 22 columns
- **Vestaboard Note:** 3 rows × 15 columns
- Configure via `VESTABOARD_BOARD_TYPE` environment variable

### API Support
- **Cloud API:** Default, uses `VESTABOARD_API_KEY`
- **Local API:** Set `VESTABOARD_LOCAL_API_KEY` for automatic detection
- Factory function automatically selects appropriate client

## Recent Changes

### Enhanced MQTT Interface & Security
- Multi-Vestaboard support via configurable topic prefixes
- Comprehensive TLS/SSL security with mutual TLS support
- Last Will and Testament (LWT) for connection monitoring
- Configurable QoS levels and connection settings
- All MQTT configuration via Pydantic models

### Board Type Support & Code Quality
- Support for Vestaboard Note (3x15) and Standard (6x22)
- BoardType constants for easy configuration
- Code refactoring: RateLimitMixin extracted (DRY principle)
- Comprehensive test suite (200+ tests with pytest)

### Local API Support
- Complete integration with Vestaboard Local API
- Automatic client selection via factory function
- Full feature parity between Cloud and Local APIs

### Modular Architecture Refactor
- Split monolithic files into focused modules
- `src/mqtt/` package: bridge, handlers, timers, topics
- `src/state/` package: state management
- `src/vestaboard/` package: client implementations
- Improved testability and maintainability

## Development Notes

### Code Quality
- Comprehensive docstrings on all classes and public methods
- Type hints throughout for better IDE support
- Pydantic models for configuration validation
- Minimal inline comments (only for complex logic)
- Code formatting: Black, isort, Flake8, Mypy, Pylint

### Testing
- 200+ tests across 8 test files
- Unit tests for individual components
- Integration tests for workflows
- Test with: `pytest --cov=src --cov-report=html`
- See [tests/README.md](tests/README.md) for details

### Dependencies
- **MQTT:** Paho MQTT client for reliable messaging
- **HTTP:** FastAPI for modern HTTP API
- **Config:** Pydantic for type-safe configuration
- **Vestaboard:** Direct REST API integration

### Logging
- Structured logging with configurable levels
- Character-by-character layout preview in DEBUG mode
- Clear operation tracking for troubleshooting

## Quick Commands

```bash
# Run locally
python run.py

# Run with Docker
docker-compose up -d

# Run tests
pytest tests/

# Format code
make format

# Run all checks
make test-all

# Interactive testing
python helpers/test_messages.py --interactive

# Monitor MQTT traffic
./helpers/monitor.sh
```

## Common Misconceptions
- Timed messages are fully implemented (not removed)
- All documentation is accurate and current
- The project is deployment-ready with Docker and Kubernetes support

---

**For complete documentation, see:**
- [README.md](README.md) - User guide and quick start
- [INTERFACE_SPEC.md](INTERFACE_SPEC.md) - Complete API specification
- [DEVELOPMENT.md](DEVELOPMENT.md) - Developer guide and tooling

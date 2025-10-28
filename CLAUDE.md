# Vestaboard MQTT Bridge - Project Context

## Overview
This project is a Python application that bridges MQTT messages to Vestaboard displays via the Read/Write API. It provides persistent save states, timed messages with auto-restore, and comprehensive monitoring capabilities.

## Project Structure
```
├── src/
│   ├── main.py                 # Application entry point
│   ├── mqtt_bridge.py          # Core MQTT bridge with timed message functionality
│   ├── vestaboard_client.py    # Vestaboard API client
│   ├── save_state_manager.py   # State persistence via MQTT retained messages
│   └── http_api.py             # FastAPI health/metrics endpoints
├── helpers/
│   ├── test_messages.py        # Interactive testing tool
│   ├── quick_test.sh          # Automated test suite
│   └── monitor.sh             # MQTT traffic monitoring
├── docker-compose.yml         # Production deployment
├── Dockerfile                 # Multi-stage container build
├── requirements.txt           # Python dependencies
└── .env.example              # Environment configuration template
```

## Core Functionality (ALL IMPLEMENTED)

### MQTT Topics
All topics use a configurable prefix (default: `vestaboard`). Examples below use the default prefix.

- `{prefix}/message` - Send text or layout array to display
- `{prefix}/save/{slot}` - Save current display state to named slot
- `{prefix}/restore/{slot}` - Restore display from named slot
- `{prefix}/delete/{slot}` - Delete saved state from named slot
- `{prefix}/timed-message` - Send timed message with auto-restore (JSON payload)
- `{prefix}/cancel-timer/{timer_id}` - Cancel active timed message
- `{prefix}/list-timers` - Query active timers
- `{prefix}/states/{slot}` - Internal retained messages storing save states

**Multi-Vestaboard Support**: Configure unique topic prefixes per instance to control multiple Vestaboards independently (e.g., `office-board`, `lobby-board`, `kitchen-board`).

### Timed Message System (FULLY IMPLEMENTED)
Located in `src/mqtt_bridge.py` lines 179-294:
- Uses Python `threading.Timer` for precise scheduling
- Auto-save current state before displaying timed message
- Auto-restore previous state after duration expires
- Timer IDs format: `timer_{unix_timestamp}`
- Active timers tracked in `self.active_timers` dictionary
- Supports custom restore slots
- Thread-safe timer operations with proper cleanup

### Key Classes
1. **VestaboardMQTTBridge** (`src/mqtt_bridge.py`)
   - Main MQTT client handling all message routing
   - Timed message scheduling and management
   - Methods: `schedule_timed_message()`, `cancel_timed_message()`, `_handle_timed_message()`

2. **VestaboardClient & LocalVestaboardClient** (`src/vestaboard_client.py`)
   - **VestaboardClient**: Handles Cloud Read/Write API interactions
   - **LocalVestaboardClient**: Handles Local API interactions
   - **BaseVestaboardClient**: Abstract base class ensuring interface compatibility
   - **RateLimitMixin**: Shared rate limiting logic (DRY principle)
   - **create_vestaboard_client()**: Factory function for automatic client selection
   - **Multi-Board Support**: Configurable board dimensions
     - BoardType.STANDARD (6x22) - Standard Vestaboard
     - BoardType.NOTE (3x15) - Vestaboard Note
     - Custom dimensions via tuple (rows, cols)
   - Supports both text messages and layout arrays of any dimension
   - Character-by-character layout previews for debugging
   - Rate limiting and message queuing for both APIs
   - Thread-safe operations with proper cleanup

3. **SaveStateManager** (`src/save_state_manager.py`)
   - Manages save/restore via MQTT retained messages
   - JSON serialization of display states
   - Automatic current state reading from Vestaboard API
   - Compatible with both Cloud and Local API clients

4. **HTTP API** (`src/http_api.py`)
   - FastAPI server for health checks and metrics
   - Endpoints: `/health`, `/ready`, `/metrics`
   - Includes active timer count in metrics

## Environment Variables

### Vestaboard API Configuration
- `VESTABOARD_API_KEY` - Vestaboard Read/Write API key (for Cloud API)
- `VESTABOARD_LOCAL_API_KEY` - Local API key (when using Local API)
- `USE_LOCAL_API` - Set to "true" to use Local API with cloud API key (optional)
- `VESTABOARD_LOCAL_HOST` - Local API hostname (default: vestaboard.local)
- `VESTABOARD_LOCAL_PORT` - Local API port (default: 7000)
- `VESTABOARD_BOARD_TYPE` - Board model configuration (default: standard)
  - "standard" = Standard Vestaboard (6 rows x 22 columns)
  - "note" = Vestaboard Note (3 rows x 15 columns)
  - "rows,cols" = Custom dimensions (e.g., "3,15")

### MQTT Configuration

#### Basic Connection
- `MQTT_BROKER_HOST` - MQTT broker hostname (default: localhost)
- `MQTT_BROKER_PORT` - MQTT broker port (default: 1883)
- `MQTT_USERNAME` - MQTT username (optional)
- `MQTT_PASSWORD` - MQTT password (optional)

#### Topic & Connection Settings
- `MQTT_TOPIC_PREFIX` - Topic prefix for all MQTT topics (default: vestaboard)
  - Use unique prefixes per instance for multi-Vestaboard deployments
  - Example: `office-board`, `lobby-display`, `kitchen-vestaboard`
- `MQTT_CLIENT_ID` - MQTT client ID (optional, auto-generated if empty)
- `MQTT_CLEAN_SESSION` - Clean session flag (default: true)
- `MQTT_KEEPALIVE` - Keep-alive interval in seconds (default: 60)
- `MQTT_QOS` - Default QoS level: 0, 1, or 2 (default: 0)

#### TLS/SSL Security (Optional)
- `MQTT_TLS_ENABLED` - Enable TLS/SSL encryption (default: false)
- `MQTT_TLS_CA_CERTS` - Path to CA certificate file (required if TLS enabled)
- `MQTT_TLS_CERTFILE` - Path to client certificate file (optional, for mutual TLS)
- `MQTT_TLS_KEYFILE` - Path to client key file (optional, for mutual TLS)
- `MQTT_TLS_INSECURE` - Skip certificate verification (default: false, INSECURE)

#### Last Will and Testament (Optional)
- `MQTT_LWT_TOPIC` - LWT topic (enables LWT if set)
- `MQTT_LWT_PAYLOAD` - LWT payload (default: "offline")
- `MQTT_LWT_QOS` - LWT QoS level (default: 0)
- `MQTT_LWT_RETAIN` - LWT retain flag (default: true)

### Application Configuration
- `HTTP_PORT` - HTTP API port (default: 8000)
- `LOG_LEVEL` - Logging level (default: INFO)

## Testing Infrastructure

### Unit & Integration Tests (Comprehensive Test Suite)
- **Test Suite**: `pytest tests/` (81+ tests, all passing)
- **Test Files**:
  - `tests/test_board_types.py` - Board type constants, character maps, text_to_layout()
  - `tests/test_vestaboard_client.py` - Client initialization, factory function
  - `tests/test_env_board_type.py` - Environment variable parsing
- **Coverage**: 50% on vestaboard_client.py (core functionality fully tested)
- **Run Tests**: `pytest --cov=src --cov-report=html`
- **Dependencies**: `pip install -r requirements-dev.txt`
- **Documentation**: See `tests/README.md` for detailed testing guide

### Manual Testing Tools
- **Interactive Testing**: `python helpers/test_messages.py --interactive`
  - Commands: `msg`, `timed`, `save`, `restore`, `timers`, `preset1/2/3`
- **Automated Testing**: `./helpers/quick_test.sh`
- **MQTT Monitoring**: `./helpers/monitor.sh`

## Deployment
- **Docker Compose**: Production-ready with health checks, resource limits
- **Kubernetes**: Includes liveness/readiness probe configuration
- **Security**: Runs as non-root user, no secrets in logs
- **Monitoring**: Built-in metrics and structured logging

## Recent Changes

### Enhanced MQTT Interface & Security (Latest Session)
- **MULTI-VESTABOARD SUPPORT**: Configurable topic prefixes enable control of multiple Vestaboards
  - `MQTT_TOPIC_PREFIX` environment variable for unique topic namespacing
  - Each instance can have its own topic prefix (e.g., `office-board`, `lobby-board`)
  - SaveStateManager updated to support dynamic topic prefixes
- **COMPREHENSIVE MQTT SECURITY**: Added full TLS/SSL and advanced connection options
  - TLS/SSL encryption with CA certificate validation
  - Mutual TLS support with client certificates
  - Configurable certificate verification (with insecure mode for testing)
  - Last Will and Testament (LWT) for connection status monitoring
  - Clean session control for persistent/non-persistent sessions
  - Configurable keep-alive intervals
  - QoS level configuration (0, 1, or 2)
  - Custom MQTT client ID support
- **BACKWARD COMPATIBLE**: All existing configurations work without changes
- **SECURITY BEST PRACTICES**:
  - TLS certificate verification enabled by default
  - Warning logs for insecure configurations
  - Support for mutual TLS authentication
  - LWT for detecting disconnected clients

### Board Type Support & Code Quality (Previous Session)
- **MULTI-BOARD SUPPORT ADDED**: Now supports Vestaboard Note (3x15) and Standard (6x22)
- **BoardType Constants**: `BoardType.STANDARD` and `BoardType.NOTE` for easy configuration
- **Environment Variable**: `VESTABOARD_BOARD_TYPE` for board model selection
- **Code Refactoring**: Extracted RateLimitMixin to eliminate ~160 lines of duplication
- **Utility Functions**: text_to_layout() and debug_layout_preview() now support any dimensions
- **Comprehensive Testing**: Added 81+ unit and integration tests (pytest)
  - test_board_types.py - Board type functionality
  - test_vestaboard_client.py - Client initialization
  - test_env_board_type.py - Environment variable parsing
- **Documentation**: Updated README.md, CLAUDE.md, Helm chart, .env.example
- **Helm Chart**: Added vestaboard.boardType configuration with conditional templating
- **Future-Proof**: Ready for any future Vestaboard models

### Local API Support (Previous)
- **LOCAL API SUPPORT ADDED**: Complete integration with Vestaboard Local API
- Added LocalVestaboardClient class with full feature parity to cloud client
- Added automatic client selection via factory function
- Environment variables added for Local API configuration
- All existing functionality preserved and compatible with both APIs
- All timed message functionality is present and working

## Development Notes
- Uses Paho MQTT client for reliable messaging
- Threading for timed message scheduling
- MQTT retained messages for state persistence
- Structured logging with configurable levels
- Character-by-character display preview in debug mode
- Comprehensive error handling throughout

## Common Misconceptions
- **Timed messages have NOT been removed** - they are fully implemented
- All README.md documentation is accurate and current
- The project is deployment-ready with complete Docker infrastructure

## MQTT Configuration Examples

### Multi-Vestaboard Deployment
Run multiple instances with unique topic prefixes to control different boards:

**Instance 1 (Office Board)**:
```bash
export VESTABOARD_API_KEY="office_api_key"
export MQTT_TOPIC_PREFIX="office-board"
export MQTT_CLIENT_ID="vestaboard-office"
export HTTP_PORT="8001"
python run.py
```

**Instance 2 (Lobby Board)**:
```bash
export VESTABOARD_API_KEY="lobby_api_key"
export MQTT_TOPIC_PREFIX="lobby-board"
export MQTT_CLIENT_ID="vestaboard-lobby"
export HTTP_PORT="8002"
python run.py
```

Now you can control each board independently:
```bash
# Update office board
mosquitto_pub -t "office-board/message" -m "Office closed today"

# Update lobby board
mosquitto_pub -t "lobby-board/message" -m "Welcome visitors!"
```

### Secure MQTT with TLS/SSL
```bash
export MQTT_BROKER_HOST="secure-mqtt.example.com"
export MQTT_BROKER_PORT="8883"
export MQTT_USERNAME="vestaboard_user"
export MQTT_PASSWORD="secure_password"
export MQTT_TLS_ENABLED="true"
export MQTT_TLS_CA_CERTS="/etc/ssl/certs/ca.crt"
export MQTT_QOS="1"  # Ensure delivery with QoS 1
export MQTT_LWT_TOPIC="vestaboard/status"
export MQTT_LWT_PAYLOAD="offline"
```

### Mutual TLS Authentication
```bash
export MQTT_BROKER_HOST="mqtt.internal.example.com"
export MQTT_BROKER_PORT="8884"
export MQTT_TLS_ENABLED="true"
export MQTT_TLS_CA_CERTS="/etc/ssl/certs/ca.crt"
export MQTT_TLS_CERTFILE="/etc/ssl/certs/vestaboard-client.crt"
export MQTT_TLS_KEYFILE="/etc/ssl/private/vestaboard-client.key"
export MQTT_CLEAN_SESSION="false"  # Persistent session
```

## Local API Configuration Examples

### Using Local API with dedicated API key
```bash
# Set Local API key (auto-detects Local API usage)
export VESTABOARD_LOCAL_API_KEY="your_local_api_key_here"
export VESTABOARD_LOCAL_HOST="vestaboard.local"  # optional
export VESTABOARD_LOCAL_PORT="7000"              # optional
```

### Using Local API with Cloud API key
```bash
# Use cloud API key but force Local API usage
export VESTABOARD_API_KEY="your_cloud_api_key"
export USE_LOCAL_API="true"
export VESTABOARD_LOCAL_HOST="192.168.1.100"     # Custom IP
```

### Cloud API (default behavior)
```bash
# Traditional cloud API usage (unchanged)
export VESTABOARD_API_KEY="your_cloud_api_key"
```

## Quick Commands for Development
```bash
# Run locally (auto-detects API type from environment)
python run.py

# Run with Docker
docker-compose up -d

# Interactive testing (works with both APIs)
python helpers/test_messages.py --interactive

# Monitor MQTT traffic
./helpers/monitor.sh

# Send timed message (works with both APIs)
mosquitto_pub -t "vestaboard/timed-message" -m '{"message": "Test", "duration_seconds": 30}'
```

This project is fully functional, well-tested, and production-ready with comprehensive timed message capabilities and dual API support (Cloud + Local) intact.
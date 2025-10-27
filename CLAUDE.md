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
- `vestaboard/message` - Send text or layout array to display
- `vestaboard/save/{slot}` - Save current display state to named slot
- `vestaboard/restore/{slot}` - Restore display from named slot
- `vestaboard/delete/{slot}` - Delete saved state from named slot
- `vestaboard/timed-message` - Send timed message with auto-restore (JSON payload)
- `vestaboard/cancel-timer/{timer_id}` - Cancel active timed message
- `vestaboard/list-timers` - Query active timers
- `vestaboard/states/{slot}` - Internal retained messages storing save states

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
   - **LocalVestaboardClient**: Handles Local API interactions (NEW)
   - **BaseVestaboardClient**: Abstract base class ensuring interface compatibility
   - **create_vestaboard_client()**: Factory function for automatic client selection
   - Supports both text messages and 6x22 layout arrays
   - Character-by-character layout previews for debugging
   - Rate limiting and message queuing for both APIs

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

### MQTT Configuration
- `MQTT_BROKER_HOST` - MQTT broker hostname (default: localhost)
- `MQTT_BROKER_PORT` - MQTT broker port (default: 1883)
- `MQTT_USERNAME` - MQTT username (optional)
- `MQTT_PASSWORD` - MQTT password (optional)

### Application Configuration
- `HTTP_PORT` - HTTP API port (default: 8000)
- `LOG_LEVEL` - Logging level (default: INFO)

## Testing Infrastructure
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
- **LOCAL API SUPPORT ADDED**: Complete integration with Vestaboard Local API
- Added LocalVestaboardClient class with full feature parity to cloud client
- Added automatic client selection via factory function
- Environment variables added for Local API configuration
- All existing functionality preserved and compatible with both APIs
- Last significant commit: 6596f08 "Remove CLAUDE.md" (documentation cleanup)
- CI/CD pipeline added recently
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
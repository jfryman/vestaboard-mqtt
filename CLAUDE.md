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

2. **VestaboardClient** (`src/vestaboard_client.py`)
   - Handles Vestaboard Read/Write API interactions
   - Supports both text messages and 6x22 layout arrays
   - Character-by-character layout previews for debugging

3. **SaveStateManager** (`src/save_state_manager.py`)
   - Manages save/restore via MQTT retained messages
   - JSON serialization of display states
   - Automatic current state reading from Vestaboard API

4. **HTTP API** (`src/http_api.py`)
   - FastAPI server for health checks and metrics
   - Endpoints: `/health`, `/ready`, `/metrics`
   - Includes active timer count in metrics

## Environment Variables
- `VESTABOARD_API_KEY` - Required Vestaboard Read/Write API key
- `MQTT_BROKER_HOST` - MQTT broker hostname (default: localhost)
- `MQTT_BROKER_PORT` - MQTT broker port (default: 1883)
- `MQTT_USERNAME` - MQTT username (optional)
- `MQTT_PASSWORD` - MQTT password (optional)
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
- Last significant commit: 6596f08 "Remove CLAUDE.md" (documentation cleanup)
- No functionality has been removed - all features remain intact
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

## Quick Commands for Development
```bash
# Run locally
python run.py

# Run with Docker
docker-compose up -d

# Interactive testing
python helpers/test_messages.py --interactive

# Monitor MQTT traffic
./helpers/monitor.sh

# Send timed message
mosquitto_pub -t "vestaboard/timed-message" -m '{"message": "Test", "duration_seconds": 30}'
```

This project is fully functional, well-tested, and production-ready with comprehensive timed message capabilities intact.
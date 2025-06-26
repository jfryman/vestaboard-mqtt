# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Vestaboard MQTT Bridge - A Python application that bridges MQTT messages to Vestaboard displays via the Read/Write API. Features include save states (storing current display to MQTT retained messages) and timed messages with auto-restore functionality.

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python run.py

# Run with environment file
cp .env.example .env
# Edit .env with your credentials
python run.py

# Testing (see helpers/README.md for details)
python3 helpers/test_messages.py --interactive  # Interactive tester
./helpers/quick_test.sh                         # Automated test suite
./helpers/monitor.sh                           # MQTT traffic monitor

# Docker
docker-compose up -d                           # Run with Docker Compose
docker-compose logs -f vestaboard-mqtt        # View logs
docker-compose down                            # Stop container
```

## Architecture

### Core Components

- **VestaboardClient** (`src/vestaboard_client.py`) - Handles Vestaboard Read/Write API interactions
- **SaveStateManager** (`src/save_state_manager.py`) - Manages save/restore functionality via MQTT retained messages
- **VestaboardMQTTBridge** (`src/mqtt_bridge.py`) - Main MQTT client handling message routing and timed messages
- **HTTP API** (`src/http_api.py`) - FastAPI server for timed message endpoints

### MQTT Topics

- `vestaboard/message` - Send text or layout array to display
- `vestaboard/save/{slot}` - Save current display state to named slot  
- `vestaboard/restore/{slot}` - Restore display from named slot
- `vestaboard/delete/{slot}` - Delete saved state from named slot
- `vestaboard/timed-message` - Send timed message with auto-restore (JSON payload)
- `vestaboard/cancel-timer/{timer_id}` - Cancel active timed message
- `vestaboard/list-timers` - Query active timers (optional response topic in payload)
- `vestaboard/states/{slot}` - Retained messages storing save states

### HTTP Endpoints (Kubernetes)

- `GET /health` - Health check for liveness probe
- `GET /ready` - Readiness check for readiness probe  
- `GET /metrics` - Basic metrics (uptime, active timers, MQTT status)

## Configuration

Required environment variables:
- `VESTABOARD_API_KEY` - Your Vestaboard Read/Write API key
- `MQTT_BROKER_HOST` - MQTT broker hostname (default: localhost)
- `MQTT_BROKER_PORT` - MQTT broker port (default: 1883)
- `HTTP_PORT` - HTTP API port (default: 8000)

Optional:
- `MQTT_USERNAME`, `MQTT_PASSWORD` - MQTT authentication
- `LOG_LEVEL` - Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)

## Logging

The application uses structured logging with configurable levels:
- **DEBUG**: Detailed debugging information including MQTT payloads and layout previews
- **INFO**: General operational messages (connections, successful operations)
- **WARNING**: Non-critical issues (missing data, fallback behaviors)
- **ERROR**: Error conditions that don't stop the application
- **CRITICAL**: Serious errors that may cause the application to terminate

Set `LOG_LEVEL=DEBUG` to see detailed character-by-character layout previews when restoring states.

## Docker Deployment

### Quick Start
```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your credentials

# Run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f vestaboard-mqtt

# Stop
docker-compose down
```

### Docker Configuration
- **Health checks**: Built-in HTTP health endpoint monitoring
- **Resource limits**: 512MB memory, 0.5 CPU cores (configurable)
- **Log rotation**: 10MB max size, 3 files retention
- **Security**: Runs as non-root user
- **Port mapping**: Uses `HTTP_PORT` from .env file (default: 8000)

### Development Override
For development with hot reload:
```bash
cp docker-compose.override.yml.example docker-compose.override.yml
# Edit override file as needed
docker-compose up -d
```
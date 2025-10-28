# Vestaboard MQTT Bridge - Interface Specification

**Version:** 1.0.0  
**Date:** June 2025  
**Service:** Vestaboard MQTT Bridge

## Overview

The Vestaboard MQTT Bridge provides a comprehensive interface for controlling Vestaboard displays via MQTT messaging and HTTP endpoints. It features state management, timed messages with auto-restore, and Kubernetes-ready health monitoring.

## MQTT Interface

### Connection Requirements

- **Protocol:** MQTT v3.1.1
- **Default Port:** 1883
- **Authentication:** Optional (username/password)
- **QoS Support:** 0, 1, 2

### Core Topics

#### `vestaboard/message`
Send text or layout arrays to display on Vestaboard.

**Payload Options:**
- Plain text string: `"Hello World"`
- JSON text object: `{"text": "Hello World"}`  
- Layout array (6x22 character codes): `[[71,72,0,0,...], ...]`

#### `vestaboard/save/{slot}`
Save current display state to named slot using MQTT retained messages.

**Topic Pattern:** `vestaboard/save/meeting-room` (slot = "meeting-room")  
**Payload:** Empty (any content ignored)  
**Storage:** Persistent via `vestaboard/states/{slot}` retained message

#### `vestaboard/restore/{slot}`
Restore display from named slot.

**Topic Pattern:** `vestaboard/restore/meeting-room`  
**Payload:** Empty (any content ignored)  
**Behavior:** Fetches from `vestaboard/states/{slot}` and displays

#### `vestaboard/delete/{slot}`
Delete saved state from named slot.

**Topic Pattern:** `vestaboard/delete/meeting-room`  
**Payload:** Empty (any content ignored)  
**Effect:** Removes retained message from `vestaboard/states/{slot}`

### Timed Messages

#### `vestaboard/timed-message`
Send timed message with automatic restore functionality.

**Payload Format (JSON):**
```json
{
  "message": "Meeting in 5 minutes!",
  "duration_seconds": 300,
  "restore_slot": "office-default",
  "response_topic": "my-app/timer-response"
}
```

**Required Fields:**
- `message` (string): Text to display

**Optional Fields:**
- `duration_seconds` (int): Display duration (default: 60)
- `restore_slot` (string): Slot to restore from (auto-saves if omitted)
- `response_topic` (string): Topic for timer confirmation response

**Response Payload:**
```json
{
  "timer_id": "timer_1719123456",
  "message": "Meeting in 5 minutes!",
  "duration_seconds": 300,
  "restore_slot": "office-default"
}
```

#### `vestaboard/cancel-timer/{timer_id}`
Cancel active timed message.

**Topic Pattern:** `vestaboard/cancel-timer/timer_1719123456`  
**Payload:** Empty (any content ignored)

#### `vestaboard/list-timers`
Query active timers.

**Payload Options:**
- Empty: Response sent to `vestaboard/timers-response`
- JSON: `{"response_topic": "my-app/timers"}`
- String: `"my-app/timers"` (response topic)

**Response Format:**
```json
{
  "active_timers": [
    {
      "timer_id": "timer_1719123456",
      "active": true,
      "created_at": "1719123456"
    }
  ],
  "total_count": 1,
  "timestamp": 1719123500
}
```

### State Storage Topics

#### `vestaboard/states/{slot}`
Retained messages containing saved display states.

**Topic Pattern:** `vestaboard/states/office-default`  
**Payload Format:**
```json
{
  "layout": [[71,72,0,0,...], ...],
  "saved_at": 1719123456,
  "original_id": "msg_abc123"
}
```

**Properties:**
- **Retained:** Yes (persistent across client sessions)
- **QoS:** 1 (reliable delivery)
- **Lifecycle:** Created by save operations, deleted by delete operations

## HTTP Interface

Base URL format: `http://host:port` (default port: 8000)

### Health & Monitoring Endpoints

#### `GET /health`
Kubernetes liveness probe endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "vestaboard-mqtt-bridge"
}
```

**Status Codes:**
- `200 OK`: Service is running

#### `GET /ready`
Kubernetes readiness probe endpoint.

**Response (Ready):**
```json
{
  "status": "ready",
  "mqtt_connected": true
}
```

**Response (Not Ready):**
```json
{
  "status": "not ready",
  "mqtt_connected": false
}
```

**Status Codes:**
- `200 OK`: Service is ready to accept traffic
- Service returns ready only when MQTT connection is active

#### `GET /metrics`
Basic operational metrics for monitoring.

**Response:**
```json
{
  "uptime_seconds": 3600.45,
  "active_timers": 2,
  "mqtt_connected": true,
  "service": "vestaboard-mqtt-bridge",
  "version": "1.0.0"
}
```

**Metrics:**
- `uptime_seconds`: Service uptime since startup
- `active_timers`: Count of running timed messages
- `mqtt_connected`: MQTT broker connection status

## Data Formats

### Layout Arrays
Vestaboard displays use character code arrays with dimensions depending on the board model.

**Board Types:**
- **Standard Vestaboard:** 6 rows × 22 columns (6x22)
- **Vestaboard Note:** 3 rows × 15 columns (3x15)

**Structure:** `[[row1], [row2], ...]` (rows vary by board type)
**Character Codes:** 0-69 (see Vestaboard API documentation)

**Example (Standard 6x22):**
```json
[
  [8,5,12,12,15,0,23,15,18,12,4,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
]
```

**Example (Vestaboard Note 3x15):**
```json
[
  [8,5,12,12,15,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
]
```

### Timer IDs
Generated with format: `timer_{unix_timestamp}`  
**Example:** `timer_1719123456`

### Slot Names
Alphanumeric strings with hyphens/underscores.  
**Valid:** `office-default`, `meeting_room`, `alert1`  
**Invalid:** Special characters, spaces, empty strings

## Error Handling

### MQTT Error Responses
- Invalid JSON payloads are logged and ignored
- Missing required fields result in operation failure (logged)
- Network disconnections trigger automatic reconnection attempts

### HTTP Error Responses
All endpoints return JSON error responses:

```json
{
  "error": "Description of error",
  "status_code": 500
}
```

### Logging Levels
Configure via `LOG_LEVEL` environment variable:
- **DEBUG:** Detailed payloads, layout previews, connection details
- **INFO:** Successful operations, connections, timer actions
- **WARNING:** Non-critical issues, fallback behaviors
- **ERROR:** Operation failures, connection errors
- **CRITICAL:** Service-threatening errors

## Integration Examples

### Basic Message Display
```bash
# Send text message
mosquitto_pub -h broker.example.com -t "vestaboard/message" -m "Hello World"

# Send layout array
mosquitto_pub -h broker.example.com -t "vestaboard/message" -m '[
  [8,5,12,12,15,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
]'
```

### State Management
```bash
# Save current display
mosquitto_pub -h broker.example.com -t "vestaboard/save/meeting-backup" -m ""

# Restore from slot
mosquitto_pub -h broker.example.com -t "vestaboard/restore/meeting-backup" -m ""

# Delete saved state
mosquitto_pub -h broker.example.com -t "vestaboard/delete/meeting-backup" -m ""
```

### Timed Messages
```bash
# 30-second urgent message with auto-restore
mosquitto_pub -h broker.example.com -t "vestaboard/timed-message" -m '{
  "message": "🚨 URGENT: Server maintenance in 5 minutes",
  "duration_seconds": 30,
  "response_topic": "alerts/timer-response"
}'

# Cancel active timer
mosquitto_pub -h broker.example.com -t "vestaboard/cancel-timer/timer_1719123456" -m ""
```

### Python Integration
```python
import paho.mqtt.client as mqtt
import json

def send_timed_alert(client, message, duration=60):
    payload = {
        "message": message,
        "duration_seconds": duration,
        "response_topic": "my-app/responses"
    }
    client.publish("vestaboard/timed-message", json.dumps(payload))

# Usage
client = mqtt.Client()
client.connect("broker.example.com", 1883, 60)
send_timed_alert(client, "Meeting starts in 10 minutes", 120)
```

## Configuration

### Environment Variables

**Vestaboard Configuration:**
- `VESTABOARD_API_KEY`: Vestaboard Cloud Read/Write API key (required*)
- `VESTABOARD_LOCAL_API_KEY`: Vestaboard Local API key (alternative to cloud)
- `USE_LOCAL_API`: Force Local API usage with cloud key (default: false)
- `VESTABOARD_LOCAL_HOST`: Local API hostname/IP (default: vestaboard.local)
- `VESTABOARD_LOCAL_PORT`: Local API port (default: 7000)
- `VESTABOARD_BOARD_TYPE`: Board model - "standard" (6x22), "note" (3x15), or "rows,cols" (default: standard)

**MQTT Configuration:**
- `MQTT_BROKER_HOST`: MQTT broker hostname (default: localhost)
- `MQTT_BROKER_PORT`: MQTT broker port (default: 1883)
- `MQTT_USERNAME`: MQTT authentication username (optional)
- `MQTT_PASSWORD`: MQTT authentication password (optional)

**Application Configuration:**
- `HTTP_PORT`: HTTP API port (default: 8000)
- `LOG_LEVEL`: Logging verbosity (default: INFO)

\* Either `VESTABOARD_API_KEY` or `VESTABOARD_LOCAL_API_KEY` is required

### Docker Deployment
```yaml
version: '3.8'
services:
  vestaboard-mqtt:
    image: vestaboard-mqtt-bridge:latest
    environment:
      - VESTABOARD_API_KEY=your_api_key_here
      - MQTT_BROKER_HOST=broker.example.com
      - MQTT_BROKER_PORT=1883
      - LOG_LEVEL=INFO
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Security Considerations

- Store API keys in secure environment variables or secrets management
- Use MQTT authentication in production environments
- Consider TLS/SSL for MQTT connections in production
- Implement network isolation for internal deployments
- Monitor logs for unauthorized access attempts

## Rate Limits & Performance

- Vestaboard API rate limits apply (check current API documentation)
- MQTT message processing is asynchronous and non-blocking  
- State management uses MQTT retained messages for persistence
- HTTP endpoints are lightweight and suitable for health monitoring
- Timed messages use Python threading for precise scheduling

## Version Compatibility

- **MQTT Protocol:** v3.1.1
- **Python:** 3.8+
- **Paho MQTT:** 1.6.0+
- **FastAPI:** 0.68.0+
- **Vestaboard API:** Read/Write API v1

## Support & Testing

### Unit & Integration Tests
```bash
# Run comprehensive test suite (81+ tests)
pytest tests/

# Run with coverage report
pytest --cov=src --cov-report=html

# Install test dependencies
pip install -r requirements-dev.txt
```

### Manual Testing Tools
```bash
# Interactive testing tool
python3 helpers/test_messages.py --interactive

# Automated test suite
./helpers/quick_test.sh

# MQTT traffic monitoring
./helpers/monitor.sh
```

See `tests/README.md` for detailed testing documentation.

---

*This specification covers the complete interface for integrating with the Vestaboard MQTT Bridge. For implementation details, see the project's CLAUDE.md file and source code documentation.*
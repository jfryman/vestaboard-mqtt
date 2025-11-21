# Vestaboard MQTT Bridge

A Python application that bridges MQTT messages to [Vestaboard](https://www.vestaboard.com/) displays via the Read/Write API. Features include persistent save states, timed messages with auto-restore, and comprehensive monitoring capabilities.

## ✨ Features

- **🔄 MQTT Integration**: Complete bridge between MQTT topics and Vestaboard displays
- **🔀 Multi-Vestaboard Support**: Control multiple boards with configurable topic prefixes
- **🔒 Secure MQTT**: TLS/SSL encryption, mutual TLS, and comprehensive security options
- **📏 Multi-Board Support**: Works with Standard Vestaboard (6x22) and Vestaboard Note (3x15)
- **🌐 Dual API Support**: Cloud Read/Write API or Local API
- **🎬 Animated Transitions**: Six animation strategies with Local API (wave, drift, curtain, row, diagonal, random)
- **💾 Save States**: Persistent state storage using MQTT retained messages with slot management
- **⏰ Timed Messages**: Display messages for specified durations with automatic restoration and optional animation
- **🎯 Smart Restoration**: Automatic save/restore functionality with timer management and optional animation
- **📊 Monitoring**: Built-in health checks, metrics, and Last Will & Testament support
- **🐳 Docker Ready**: Complete containerization with security and monitoring
- **🔍 Debug Friendly**: Character-by-character layout previews and structured logging
- **🛠️ Developer Tools**: Interactive testing suite and monitoring scripts
- **✅ Fully Tested**: Comprehensive test suite with 81+ tests

## 🚀 Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone and setup
git clone <repository-url>
cd vestaboard-mqtt

# Configure environment
cp .env.example .env
# Edit .env with your Vestaboard API key and MQTT broker details

# Run with Docker
docker-compose up -d

# View logs
docker-compose logs -f vestaboard-mqtt

# Check health
curl http://localhost:8000/health
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run application
python run.py
```

## 📋 Prerequisites

1. **Vestaboard Display** with Read/Write API access
2. **MQTT Broker** (like Mosquitto, Home Assistant, or cloud MQTT service)
3. **Vestaboard API Key** from the mobile app or web interface

### Getting Your Vestaboard API Key

1. Open the Vestaboard mobile app or visit the web app
2. Go to **Settings** → **Developer**
3. Enable the **Read / Write API**
4. Copy the generated API key

## 📡 MQTT Topics

All topics use a configurable prefix (default: `vestaboard`). Set `MQTT_TOPIC_PREFIX` to customize.

### Core Operations
- `{prefix}/message` - Send text or layout array to display
- `{prefix}/message/{strategy}` - Send animated message with transitions (Local API only)
- `{prefix}/save/{slot}` - Save current display state to named slot
- `{prefix}/restore/{slot}` - Restore display from named slot
- `{prefix}/delete/{slot}` - Delete saved state from named slot

### Timed Messages
- `{prefix}/timed-message` - Send timed message with auto-restore (JSON payload)
- `{prefix}/cancel-timer/{timer_id}` - Cancel active timed message
- `{prefix}/list-timers` - Query active timers

### Internal Storage
- `{prefix}/states/{slot}` - Retained messages storing save states

### Multi-Vestaboard Example
```bash
# Control office board (prefix: office-board)
mosquitto_pub -t "office-board/message" -m "Meeting at 3pm"

# Control lobby board (prefix: lobby-board)
mosquitto_pub -t "lobby-board/message" -m "Welcome!"
```

### Animated Message Example (Local API)
```bash
# Send message with wave effect
mosquitto_pub -t "vestaboard/message/column" -m "Hello World"

# Curtain effect with text
mosquitto_pub -t "vestaboard/message/edges-to-center" -m "Welcome!"

# Diagonal animation with layout array
mosquitto_pub -t "vestaboard/message/diagonal" -m '[[71,72,0,0,...], ...]'

# Custom timing with JSON parameters
mosquitto_pub -t "vestaboard/message/random" -m '{
  "text": "Surprise!",
  "step_interval_ms": 2000,
  "step_size": 3
}'
```

Available animation strategies: `column` (wave), `reverse-column` (drift), `edges-to-center` (curtain), `row`, `diagonal`, `random`

Optional timing parameters: `step_interval_ms` (delay between steps), `step_size` (number of simultaneous updates)

## 🔧 Configuration

### Environment Variables

#### Vestaboard Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `VESTABOARD_API_KEY` | Vestaboard Cloud Read/Write API key | **Required*** |
| `VESTABOARD_LOCAL_API_KEY` | Vestaboard Local API key (alternative to cloud) | - |
| `USE_LOCAL_API` | Force Local API usage with cloud API key | `false` |
| `VESTABOARD_LOCAL_HOST` | Local API hostname/IP | `vestaboard.local` |
| `VESTABOARD_LOCAL_PORT` | Local API port | `7000` |
| `VESTABOARD_BOARD_TYPE` | Board model: `standard` (6x22), `note` (3x15), or `rows,cols` | `standard` |

\* Either `VESTABOARD_API_KEY` or `VESTABOARD_LOCAL_API_KEY` is required

#### MQTT Configuration

##### Basic Connection
| Variable | Description | Default |
|----------|-------------|---------|
| `MQTT_BROKER_HOST` | MQTT broker hostname | `localhost` |
| `MQTT_BROKER_PORT` | MQTT broker port | `1883` |
| `MQTT_USERNAME` | MQTT username (optional) | - |
| `MQTT_PASSWORD` | MQTT password (optional) | - |

##### Topics & Connection
| Variable | Description | Default |
|----------|-------------|---------|
| `MQTT_TOPIC_PREFIX` | Topic prefix for all MQTT topics | `vestaboard` |
| `MQTT_CLIENT_ID` | MQTT client ID (empty for auto-generate) | - |
| `MQTT_CLEAN_SESSION` | Clean session on reconnect | `true` |
| `MQTT_KEEPALIVE` | Keep-alive interval (seconds) | `60` |
| `MQTT_QOS` | Default QoS level (0, 1, or 2) | `0` |

##### TLS/SSL Security (Optional)
| Variable | Description | Default |
|----------|-------------|---------|
| `MQTT_TLS_ENABLED` | Enable TLS/SSL encryption | `false` |
| `MQTT_TLS_CA_CERTS` | Path to CA certificate file | - |
| `MQTT_TLS_CERTFILE` | Path to client cert (mutual TLS) | - |
| `MQTT_TLS_KEYFILE` | Path to client key (mutual TLS) | - |
| `MQTT_TLS_INSECURE` | Skip cert verification (testing only) | `false` |

##### Last Will & Testament (Optional)
| Variable | Description | Default |
|----------|-------------|---------|
| `MQTT_LWT_TOPIC` | LWT topic (enables if set) | - |
| `MQTT_LWT_PAYLOAD` | LWT message payload | `offline` |
| `MQTT_LWT_QOS` | LWT QoS level | `0` |
| `MQTT_LWT_RETAIN` | Retain LWT message | `true` |

#### Application Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `HTTP_PORT` | HTTP API port | `8000` |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |

### Example .env Files

#### Standard Vestaboard with Cloud API
```bash
VESTABOARD_API_KEY=your_api_key_here
VESTABOARD_BOARD_TYPE=standard  # 6 rows x 22 columns (default)
MQTT_BROKER_HOST=homeassistant.local
MQTT_BROKER_PORT=1883
MQTT_USERNAME=mqtt_user
MQTT_PASSWORD=mqtt_pass
MQTT_TOPIC_PREFIX=vestaboard  # default prefix
HTTP_PORT=8000
LOG_LEVEL=INFO
```

#### Multi-Vestaboard Setup (Office Board)
```bash
VESTABOARD_API_KEY=office_api_key_here
VESTABOARD_BOARD_TYPE=standard
MQTT_BROKER_HOST=mqtt.local
MQTT_BROKER_PORT=1883
MQTT_USERNAME=mqtt_user
MQTT_PASSWORD=mqtt_pass
MQTT_TOPIC_PREFIX=office-board  # unique prefix for this board
MQTT_CLIENT_ID=vestaboard-office
HTTP_PORT=8001
LOG_LEVEL=INFO
```

#### Secure MQTT with TLS/SSL
```bash
VESTABOARD_API_KEY=your_api_key_here
MQTT_BROKER_HOST=secure-mqtt.example.com
MQTT_BROKER_PORT=8883
MQTT_USERNAME=mqtt_user
MQTT_PASSWORD=mqtt_pass
MQTT_TLS_ENABLED=true
MQTT_TLS_CA_CERTS=/etc/ssl/certs/ca.crt
MQTT_QOS=1  # ensure message delivery
MQTT_LWT_TOPIC=vestaboard/status
MQTT_LWT_PAYLOAD=offline
HTTP_PORT=8000
LOG_LEVEL=INFO
```

#### Vestaboard Note with Local API
```bash
VESTABOARD_LOCAL_API_KEY=your_local_api_key_here
VESTABOARD_BOARD_TYPE=note  # 3 rows x 15 columns
VESTABOARD_LOCAL_HOST=192.168.1.100
VESTABOARD_LOCAL_PORT=7000
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
HTTP_PORT=8000
LOG_LEVEL=INFO
```

## 💡 Usage Examples

### Basic Messages

```bash
# Send simple text
mosquitto_pub -t "vestaboard/message" -m "Hello World!"

# Send JSON text message
mosquitto_pub -t "vestaboard/message" -m '{"text": "Welcome Home"}'
```

### Save & Restore States

```bash
# Save current display to slot "backup1"
mosquitto_pub -t "vestaboard/save/backup1" -m ""

# Restore from slot "backup1" (instant)
mosquitto_pub -t "vestaboard/restore/backup1" -m ""

# Restore with animation (Local API only)
mosquitto_pub -t "vestaboard/restore/backup1" -m '{
  "strategy": "column",
  "step_interval_ms": 1500
}'

# Delete saved state
mosquitto_pub -t "vestaboard/delete/backup1" -m ""
```

### Timed Messages

```bash
# Display message for 30 seconds then auto-restore
mosquitto_pub -t "vestaboard/timed-message" -m '{
  "message": "Meeting in 5 minutes!",
  "duration_seconds": 30
}'

# Timed message with specific restore slot
mosquitto_pub -t "vestaboard/timed-message" -m '{
  "message": "Emergency Alert!",
  "duration_seconds": 60,
  "restore_slot": "normal_display"
}'

# Animated timed message (Local API only)
mosquitto_pub -t "vestaboard/timed-message" -m '{
  "message": "Meeting Starting!",
  "duration_seconds": 30,
  "strategy": "edges-to-center",
  "step_interval_ms": 1000
}'

# Animated timed message with different restore animation
mosquitto_pub -t "vestaboard/timed-message" -m '{
  "message": "Alert!",
  "duration_seconds": 45,
  "strategy": "column",
  "restore_strategy": "reverse-column"
}'

# List active timers
mosquitto_pub -t "vestaboard/list-timers" -m ""
```

### Timer Management

```bash
# Cancel specific timer
mosquitto_pub -t "vestaboard/cancel-timer/timer_1703123456" -m ""
```

## 🏥 Health & Monitoring

### HTTP Endpoints

- `GET /health` - Health check for liveness probes
- `GET /ready` - Readiness check (validates MQTT connection)
- `GET /metrics` - Basic metrics (uptime, active timers, MQTT status)

### Kubernetes Integration

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vestaboard-mqtt
spec:
  template:
    spec:
      containers:
      - name: vestaboard-mqtt
        image: vestaboard-mqtt:latest
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        env:
        - name: VESTABOARD_API_KEY
          valueFrom:
            secretKeyRef:
              name: vestaboard-secret
              key: api-key
```

## 🧪 Testing

### Interactive Testing

```bash
# Start interactive test tool
python3 helpers/test_messages.py --interactive

# Available commands in interactive mode:
# msg <text>              - Send regular message
# timed <text> [duration] - Send timed message
# save <slot>             - Save current state
# restore <slot>          - Restore state
# timers                  - List active timers
# preset1/2/3            - Quick demo messages
```

### Automated Testing

```bash
# Run complete test suite
./helpers/quick_test.sh

# Monitor MQTT traffic
./helpers/monitor.sh
```

## 🐳 Docker Deployment

### Production

```bash
# Build and run
docker-compose up -d

# Scale if needed
docker-compose up -d --scale vestaboard-mqtt=2

# Update
docker-compose pull && docker-compose up -d
```

### Development

```bash
# Setup development overrides
cp docker-compose.override.yml.example docker-compose.override.yml

# Run with hot reload and debug logging
docker-compose up -d
```

### Docker Features

- **Security**: Runs as non-root user
- **Health Checks**: Built-in HTTP endpoint monitoring
- **Resource Limits**: 512MB memory, 0.5 CPU cores
- **Log Rotation**: 10MB max size, 3 files retention
- **Auto-restart**: Container restarts on failure

## 📝 Logging

The application provides structured logging with configurable levels:

- **DEBUG**: Detailed debugging including character-by-character layout previews
- **INFO**: General operational messages (default)
- **WARNING**: Non-critical issues
- **ERROR**: Error conditions
- **CRITICAL**: Serious errors

Set `LOG_LEVEL=DEBUG` to see detailed layout character mapping when debugging display issues.

## 🏗️ Architecture

### Core Components

- **VestaboardClient**: Handles Vestaboard Read/Write API interactions
- **SaveStateManager**: Manages save/restore functionality via MQTT retained messages
- **VestaboardMQTTBridge**: Main MQTT client handling message routing and timed messages
- **HTTP API**: FastAPI server for health checks and metrics

### Message Flow

1. MQTT messages received on subscribed topics
2. Messages parsed and validated
3. Appropriate handler called (save, restore, timed message, etc.)
4. Vestaboard API called with proper formatting
5. Response logged with character preview (if applicable)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with the provided helpers
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [Vestaboard](https://www.vestaboard.com/) for the amazing display hardware and API
- [Paho MQTT](https://www.eclipse.org/paho/) for reliable MQTT client library
- [FastAPI](https://fastapi.tiangolo.com/) for the modern HTTP API framework

## 🔗 Related Projects

- [Home Assistant Vestaboard Integration](https://www.home-assistant.io/integrations/vestaboard/)
- [Vestaboard Python SDK](https://github.com/ShaneSutro/Vestaboard)

---

**Made with ❤️ for the Vestaboard community**
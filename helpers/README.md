# Vestaboard MQTT Bridge - Test Helpers

This directory contains helper scripts and tools for testing the Vestaboard MQTT Bridge functionality.

## 🧪 Test Scripts

### 1. Python Interactive Tester (`test_messages.py`)

Full-featured Python script for testing all bridge functionality.

**Usage:**
```bash
# Interactive mode
python3 helpers/test_messages.py --interactive

# Single commands
python3 helpers/test_messages.py --message "Hello World"
python3 helpers/test_messages.py --timed-message "Emergency!" --duration 30
python3 helpers/test_messages.py --save backup1
python3 helpers/test_messages.py --restore backup1
python3 helpers/test_messages.py --list-timers

# With custom MQTT broker
python3 helpers/test_messages.py --host mqtt.example.com --port 8883 --username user --password pass --interactive
```

**Interactive Commands:**
- `msg <text>` - Send regular message
- `timed <text> [duration]` - Send timed message
- `save <slot>` - Save current state
- `restore <slot>` - Restore state
- `delete <slot>` - Delete saved state
- `timers` - List active timers
- `cancel <timer_id>` - Cancel timer
- `preset1/2/3` - Quick demo messages
- `quit` - Exit

### 2. Quick Test Script (`quick_test.sh`)

Bash script that runs through all major functionality automatically.

**Usage:**
```bash
# Make executable
chmod +x helpers/quick_test.sh

# Run with default settings (localhost:1883)
./helpers/quick_test.sh

# Run with custom MQTT broker
MQTT_HOST=mqtt.example.com MQTT_PORT=8883 ./helpers/quick_test.sh

# With authentication
MQTT_HOST=broker.hivemq.com MQTT_USER=user MQTT_PASS=password ./helpers/quick_test.sh
```

**Test Sequence:**
1. Send basic message
2. Save current state
3. Send 10-second timed message
4. Send timed message with restore
5. List active timers
6. Test timer cancellation
7. Restore from backup
8. Clean up

### 3. Monitor Script (`monitor.sh`)

Real-time MQTT traffic monitor to see all bridge activity.

**Usage:**
```bash
# Make executable
chmod +x helpers/monitor.sh

# Start monitoring
./helpers/monitor.sh

# Monitor remote broker
MQTT_HOST=mqtt.example.com ./helpers/monitor.sh
```

## 🚀 Quick Start Testing

1. **Start the bridge:**
   ```bash
   python run.py
   ```

2. **Monitor traffic (in another terminal):**
   ```bash
   ./helpers/monitor.sh
   ```

3. **Run interactive tester (in third terminal):**
   ```bash
   python3 helpers/test_messages.py --interactive
   ```

4. **Try some commands:**
   ```
   🤖 > msg Hello World!
   🤖 > save backup1
   🤖 > timed Emergency Alert! 15
   🤖 > timers
   🤖 > restore backup1
   🤖 > quit
   ```

## 📋 Environment Variables

All scripts support these environment variables:

- `MQTT_HOST` - MQTT broker hostname (default: localhost)
- `MQTT_PORT` - MQTT broker port (default: 1883)
- `MQTT_USER` - MQTT username (optional)
- `MQTT_PASS` - MQTT password (optional)

## 🎯 Preset Test Messages

The interactive tester includes preset messages for quick testing:

- `preset1` - "Meeting in 5 minutes!" (10 seconds)
- `preset2` - "🚨 URGENT ALERT 🚨" (30 seconds)  
- `preset3` - "☕ Coffee Time! ☕" (60 seconds)

## 🔧 Requirements

- Python 3.7+ with `paho-mqtt` package
- `mosquitto-clients` for bash scripts
- Running Vestaboard MQTT Bridge
- Access to MQTT broker

## 💡 Tips

- Use the monitor script to see real-time MQTT traffic
- Save states before testing timed messages so you can restore
- Timer IDs are based on timestamps: `timer_1703123456`
- Response topics can be customized for each operation
- All scripts support custom MQTT broker configurations
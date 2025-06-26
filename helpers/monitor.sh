#!/bin/bash
# Monitor script to watch all Vestaboard MQTT traffic

# Configuration
MQTT_HOST="${MQTT_HOST:-localhost}"
MQTT_PORT="${MQTT_PORT:-1883}"
MQTT_USER="${MQTT_USER:-}"
MQTT_PASS="${MQTT_PASS:-}"

# Build mosquitto_sub command
MQTT_CMD="mosquitto_sub -h $MQTT_HOST -p $MQTT_PORT"
if [ -n "$MQTT_USER" ] && [ -n "$MQTT_PASS" ]; then
    MQTT_CMD="$MQTT_CMD -u $MQTT_USER -P $MQTT_PASS"
fi

echo "👁️ Vestaboard MQTT Bridge - Traffic Monitor"
echo "📡 Monitoring MQTT broker: $MQTT_HOST:$MQTT_PORT"
echo "🔍 Watching topics: vestaboard/# and test/#"
echo "Press Ctrl+C to stop monitoring"
echo "=========================================="

# Subscribe to all vestaboard topics and test topics
$MQTT_CMD -t "vestaboard/+/+" -t "vestaboard/+" -t "test/+" -v
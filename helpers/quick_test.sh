#!/bin/bash
# Quick test script for Vestaboard MQTT Bridge using mosquitto_pub

set -e

# Configuration
MQTT_HOST="${MQTT_HOST:-localhost}"
MQTT_PORT="${MQTT_PORT:-1883}"
MQTT_USER="${MQTT_USER:-}"
MQTT_PASS="${MQTT_PASS:-}"

# Build mosquitto_pub command
MQTT_CMD="mosquitto_pub -h $MQTT_HOST -p $MQTT_PORT"
if [ -n "$MQTT_USER" ] && [ -n "$MQTT_PASS" ]; then
    MQTT_CMD="$MQTT_CMD -u $MQTT_USER -P $MQTT_PASS"
fi

echo "🚀 Vestaboard MQTT Bridge - Quick Test Script"
echo "📡 Using MQTT broker: $MQTT_HOST:$MQTT_PORT"
echo

# Function to send message
send_message() {
    local topic="$1"
    local payload="$2"
    echo "📤 Sending to $topic: $payload"
    $MQTT_CMD -t "$topic" -m "$payload"
}

# Function to wait with countdown
wait_with_countdown() {
    local seconds=$1
    local message="$2"
    echo "$message"
    for ((i=seconds; i>=1; i--)); do
        printf "\r⏳ Waiting %d seconds..." $i
        sleep 1
    done
    printf "\r✅ Done waiting!           \n"
}

echo "1️⃣ Testing basic message..."
send_message "vestaboard/message" "Hello from test script!"
sleep 2

echo
echo "2️⃣ Saving current state to 'test-backup'..."
send_message "vestaboard/save/test-backup" ""
sleep 2

echo
echo "3️⃣ Testing 10-second timed message..."
send_message "vestaboard/timed-message" '{
  "message": "⏰ TIMED TEST MESSAGE ⏰",
  "duration_seconds": 10,
  "response_topic": "test/timer-response"
}'
wait_with_countdown 12 "Timer should expire in 10 seconds..."

echo
echo "4️⃣ Testing another timed message with restore slot..."
send_message "vestaboard/timed-message" '{
  "message": "☕ Coffee Break! ☕",
  "duration_seconds": 8,
  "restore_slot": "test-backup"
}'
wait_with_countdown 10 "Coffee break message should restore in 8 seconds..."

echo
echo "5️⃣ Listing active timers..."
send_message "vestaboard/list-timers" ""
sleep 2

echo
echo "6️⃣ Testing cancellable timer..."
send_message "vestaboard/timed-message" '{
  "message": "🔥 WILL BE CANCELLED 🔥",
  "duration_seconds": 60,
  "response_topic": "test/cancel-response"
}'
echo "🎯 Started 60-second timer - will cancel in 3 seconds..."
sleep 3

# Get timer ID from recent timestamp (approximate)
TIMER_ID="timer_$(date +%s)"
echo "❌ Attempting to cancel timer (Note: exact timer ID needed for real cancellation)"
send_message "vestaboard/cancel-timer/$TIMER_ID" ""
sleep 2

echo
echo "7️⃣ Restoring from backup..."
send_message "vestaboard/restore/test-backup" ""
sleep 2

echo
echo "8️⃣ Cleaning up - deleting test backup..."
send_message "vestaboard/delete/test-backup" ""
sleep 2

echo
echo "✅ Test script completed!"
echo "📝 Note: To see responses, run in another terminal:"
echo "   mosquitto_sub -h $MQTT_HOST -p $MQTT_PORT -t 'vestaboard/+' -t 'test/+'"
echo
echo "🎮 For interactive testing, use:"
echo "   python3 helpers/test_messages.py --interactive"
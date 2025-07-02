#!/bin/bash
# Quick test script for Vestaboard MQTT Bridge using mosquitto_pub

set -e

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Configuration - Uses same variables as .env.example
MQTT_BROKER_HOST="${MQTT_BROKER_HOST:-localhost}"
MQTT_BROKER_PORT="${MQTT_BROKER_PORT:-1883}"
MQTT_USERNAME="${MQTT_USERNAME:-}"
MQTT_PASSWORD="${MQTT_PASSWORD:-}"

# Build mosquitto_pub command
MQTT_CMD="mosquitto_pub -h $MQTT_BROKER_HOST -p $MQTT_BROKER_PORT"
if [ -n "$MQTT_USERNAME" ] && [ -n "$MQTT_PASSWORD" ]; then
    MQTT_CMD="$MQTT_CMD -u $MQTT_USERNAME -P $MQTT_PASSWORD"
fi

echo "🚀 Vestaboard MQTT Bridge - Quick Test Script"
echo "📡 Using MQTT broker: $MQTT_BROKER_HOST:$MQTT_BROKER_PORT"
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
echo "8️⃣ Testing smart restore logic (edge case)..."
echo "📝 This tests the new feature where timed messages don't restore if display was changed"
send_message "vestaboard/message" "Initial Smart Test State"
sleep 2
send_message "vestaboard/save/smart-test-backup" ""
sleep 2
echo "🕐 Starting 15-second timed message..."
send_message "vestaboard/timed-message" '{
  "message": "⏱️ SMART TIMER TEST ⏱️",
  "duration_seconds": 15,
  "restore_slot": "smart-test-backup"
}'
wait_with_countdown 5 "Letting timed message display for 5 seconds..."
echo "🚨 Sending alert to override timed message..."
send_message "vestaboard/message" "🚨 URGENT ALERT! 🚨"
wait_with_countdown 12 "Timer will expire in ~10 seconds. Should NOT restore due to alert override..."
echo "📊 Result: If display still shows 'URGENT ALERT!' then smart restore worked!"
sleep 2

echo
echo "9️⃣ Testing normal restore behavior (control test)..."
send_message "vestaboard/message" "Normal Restore Test State"
sleep 2
send_message "vestaboard/save/normal-test-backup" ""
sleep 2
echo "🕐 Starting 8-second timed message that should restore normally..."
send_message "vestaboard/timed-message" '{
  "message": "⏱️ NORMAL TIMER TEST ⏱️",
  "duration_seconds": 8,
  "restore_slot": "normal-test-backup"
}'
wait_with_countdown 10 "Timer should restore in 8 seconds (no interruption)..."
echo "📊 Result: Display should show 'Normal Restore Test State' (restored)"
sleep 2

echo
echo "🔟 Cleaning up test backups..."
send_message "vestaboard/delete/test-backup" ""
send_message "vestaboard/delete/smart-test-backup" ""
send_message "vestaboard/delete/normal-test-backup" ""
sleep 2

echo
echo "✅ Test script completed!"
echo "📊 Smart Restore Test Summary:"
echo "   - Test 8: Alert should override timer (no restore)"
echo "   - Test 9: Normal timer should restore properly"
echo "📝 Note: To see responses, run in another terminal:"
echo "   mosquitto_sub -h $MQTT_BROKER_HOST -p $MQTT_BROKER_PORT -t 'vestaboard/+' -t 'test/+'"
echo
echo "🎮 For interactive testing, use:"
echo "   python3 helpers/test_messages.py --interactive"

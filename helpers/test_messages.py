#!/usr/bin/env python3
"""Helper script to generate test timed messages for Vestaboard MQTT Bridge."""

import json
import time
import argparse
import paho.mqtt.client as mqtt
from typing import Optional


class VestaboardTester:
    """Helper class for testing Vestaboard MQTT functionality."""
    
    def __init__(self, broker_host: str = "localhost", broker_port: int = 1883, 
                 username: Optional[str] = None, password: Optional[str] = None):
        """Initialize the tester.
        
        Args:
            broker_host: MQTT broker host
            broker_port: MQTT broker port
            username: MQTT username (optional)
            password: MQTT password (optional)
        """
        self.client = mqtt.Client()
        self.broker_host = broker_host
        self.broker_port = broker_port
        
        # Set up authentication if provided
        if username and password:
            self.client.username_pw_set(username, password)
        
        # Set up callbacks
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        
        # Connect to broker
        try:
            self.client.connect(broker_host, broker_port, 60)
            self.client.loop_start()
            print(f"Connected to MQTT broker at {broker_host}:{broker_port}")
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")
            raise
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for MQTT connection."""
        if rc == 0:
            print("Successfully connected to MQTT broker")
            # Subscribe to response topics
            client.subscribe("vestaboard/timers-response")
            client.subscribe("vestaboard/timer-response")
        else:
            print(f"Failed to connect: {rc}")
    
    def _on_message(self, client, userdata, message):
        """Handle incoming MQTT messages."""
        topic = message.topic
        payload = message.payload.decode('utf-8')
        print(f"\n📥 Response on {topic}:")
        try:
            data = json.loads(payload)
            print(json.dumps(data, indent=2))
        except json.JSONDecodeError:
            print(payload)
        print()
    
    def send_message(self, message: str):
        """Send a regular message to Vestaboard.
        
        Args:
            message: Text message to display
        """
        self.client.publish("vestaboard/message", message)
        print(f"📤 Sent message: '{message}'")
    
    def send_timed_message(self, message: str, duration: int = 30, 
                          restore_slot: Optional[str] = None, 
                          response_topic: Optional[str] = None):
        """Send a timed message to Vestaboard.
        
        Args:
            message: Text message to display
            duration: Duration in seconds
            restore_slot: Optional slot to restore from
            response_topic: Optional response topic
        """
        payload = {
            "message": message,
            "duration_seconds": duration,
        }
        
        if restore_slot:
            payload["restore_slot"] = restore_slot
        
        if response_topic:
            payload["response_topic"] = response_topic
        
        self.client.publish("vestaboard/timed-message", json.dumps(payload))
        print(f"⏰ Sent timed message: '{message}' for {duration}s")
        if restore_slot:
            print(f"   Will restore from slot: {restore_slot}")
    
    def save_state(self, slot: str):
        """Save current Vestaboard state to a slot.
        
        Args:
            slot: Slot name to save to
        """
        self.client.publish(f"vestaboard/save/{slot}", "")
        print(f"💾 Saved current state to slot: {slot}")
    
    def restore_state(self, slot: str):
        """Restore Vestaboard state from a slot.
        
        Args:
            slot: Slot name to restore from
        """
        self.client.publish(f"vestaboard/restore/{slot}", "")
        print(f"♻️ Restored state from slot: {slot}")
    
    def delete_state(self, slot: str):
        """Delete a saved state.
        
        Args:
            slot: Slot name to delete
        """
        self.client.publish(f"vestaboard/delete/{slot}", "")
        print(f"🗑️ Deleted saved state from slot: {slot}")
    
    def list_timers(self, response_topic: str = "vestaboard/timers-response"):
        """List active timers.
        
        Args:
            response_topic: Topic to receive response on
        """
        payload = {"response_topic": response_topic} if response_topic != "vestaboard/timers-response" else ""
        self.client.publish("vestaboard/list-timers", json.dumps(payload) if payload else "")
        print(f"📋 Requested timer list (response on: {response_topic})")
    
    def cancel_timer(self, timer_id: str):
        """Cancel an active timer.
        
        Args:
            timer_id: Timer ID to cancel
        """
        self.client.publish(f"vestaboard/cancel-timer/{timer_id}", "")
        print(f"❌ Cancelled timer: {timer_id}")
    
    def disconnect(self):
        """Disconnect from MQTT broker."""
        self.client.loop_stop()
        self.client.disconnect()
        print("Disconnected from MQTT broker")


def main():
    """Main function with CLI interface."""
    parser = argparse.ArgumentParser(description="Vestaboard MQTT Bridge Tester")
    parser.add_argument("--host", default="localhost", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--username", help="MQTT username")
    parser.add_argument("--password", help="MQTT password")
    parser.add_argument("--interactive", "-i", action="store_true", 
                       help="Interactive mode")
    
    # Command arguments
    parser.add_argument("--message", help="Send a regular message")
    parser.add_argument("--timed-message", help="Send a timed message")
    parser.add_argument("--duration", type=int, default=30, 
                       help="Duration for timed message (seconds)")
    parser.add_argument("--restore-slot", help="Slot to restore from after timer")
    parser.add_argument("--save", help="Save current state to slot")
    parser.add_argument("--restore", help="Restore state from slot")
    parser.add_argument("--delete", help="Delete saved state from slot")
    parser.add_argument("--list-timers", action="store_true", 
                       help="List active timers")
    parser.add_argument("--cancel-timer", help="Cancel timer by ID")
    
    args = parser.parse_args()
    
    # Create tester instance
    try:
        tester = VestaboardTester(
            args.host, args.port, args.username, args.password
        )
        time.sleep(1)  # Allow connection to establish
    except Exception as e:
        print(f"Failed to initialize tester: {e}")
        return 1
    
    try:
        if args.interactive:
            interactive_mode(tester)
        else:
            # Execute single commands
            if args.message:
                tester.send_message(args.message)
            
            if args.timed_message:
                tester.send_timed_message(
                    args.timed_message, 
                    args.duration, 
                    args.restore_slot
                )
            
            if args.save:
                tester.save_state(args.save)
            
            if args.restore:
                tester.restore_state(args.restore)
            
            if args.delete:
                tester.delete_state(args.delete)
            
            if args.list_timers:
                tester.list_timers()
            
            if args.cancel_timer:
                tester.cancel_timer(args.cancel_timer)
            
            # Wait a bit for responses
            if any([args.timed_message, args.list_timers, args.save, 
                   args.restore, args.delete, args.cancel_timer]):
                print("Waiting for responses...")
                time.sleep(2)
    
    finally:
        tester.disconnect()
    
    return 0


def interactive_mode(tester: VestaboardTester):
    """Interactive mode for testing."""
    print("\n🎮 Interactive Mode - Vestaboard MQTT Tester")
    print("Available commands:")
    print("  msg <text>              - Send regular message")
    print("  timed <text> [duration] - Send timed message (default 30s)")
    print("  save <slot>             - Save current state")
    print("  restore <slot>          - Restore state from slot")
    print("  delete <slot>           - Delete saved state")
    print("  timers                  - List active timers")
    print("  cancel <timer_id>       - Cancel timer")
    print("  preset1                 - Demo: 'Meeting in 5 min' for 10s")
    print("  preset2                 - Demo: 'URGENT ALERT' for 30s")
    print("  preset3                 - Demo: 'Coffee Time!' for 60s")
    print("  help                    - Show this help")
    print("  quit                    - Exit")
    print()
    
    while True:
        try:
            cmd = input("🤖 > ").strip().split()
            if not cmd:
                continue
            
            if cmd[0] == "quit":
                break
            elif cmd[0] == "help":
                # Re-print help
                interactive_mode.__doc__
                continue
            elif cmd[0] == "msg" and len(cmd) > 1:
                tester.send_message(" ".join(cmd[1:]))
            elif cmd[0] == "timed" and len(cmd) > 1:
                duration = int(cmd[2]) if len(cmd) > 2 else 30
                tester.send_timed_message(" ".join(cmd[1:2]), duration)
            elif cmd[0] == "save" and len(cmd) > 1:
                tester.save_state(cmd[1])
            elif cmd[0] == "restore" and len(cmd) > 1:
                tester.restore_state(cmd[1])
            elif cmd[0] == "delete" and len(cmd) > 1:
                tester.delete_state(cmd[1])
            elif cmd[0] == "timers":
                tester.list_timers()
            elif cmd[0] == "cancel" and len(cmd) > 1:
                tester.cancel_timer(cmd[1])
            elif cmd[0] == "preset1":
                tester.send_timed_message("Meeting in 5 minutes!", 10)
            elif cmd[0] == "preset2":
                tester.send_timed_message("🚨 URGENT ALERT 🚨", 30)
            elif cmd[0] == "preset3":
                tester.send_timed_message("☕ Coffee Time! ☕", 60)
            else:
                print("❓ Unknown command. Type 'help' for available commands.")
        
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    exit(main())
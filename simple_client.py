#!/usr/bin/env python3
"""
Simple Manual Test Client for Sanskara AI
Quick and easy testing of the WebSocket functionality
"""

import asyncio
import websockets
import json
import sys
from datetime import datetime

# Configuration
WS_URL = "ws://localhost:8765/ws"
USER_ID = "fca04215-2af3-4a4e-bcfa-c27a4f54474c"

class SimpleClient:
    def __init__(self):
        self.websocket = None
        self.connected = False
    
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    async def connect(self):
        """Connect to the WebSocket server"""
        try:
            ws_url_with_user = f"{WS_URL}?user_id={USER_ID}"
            self.log(f"Connecting to {ws_url_with_user}")
            self.websocket = await websockets.connect(ws_url_with_user)
            # Expect an init first, then ready
            first_msg = await self.websocket.recv()
            try:
                first_data = json.loads(first_msg)
            except Exception:
                first_data = {}
            if first_data.get("type") == "init":
                self.log("⏳ Initializing context...")
                # Wait for ready
                ready_message = await self.websocket.recv()
                ready_data = json.loads(ready_message)
            else:
                ready_data = first_data
            if ready_data.get("type") == "ready":
                self.connected = True
                self.log("✅ Connected successfully (context primed)!")
                return True
            else:
                self.log(f"❌ Unexpected handshake messages: {first_data} then {ready_data}")
                return False
        except Exception as e:
            self.log(f"❌ Connection failed: {e}")
            return False
    
    async def send_message(self, text):
        """Send a text message"""
        if not self.connected or not self.websocket:
            self.log("❌ Not connected!")
            return
        
        try:
            message = {
                "type": "text",
                "data": text
            }
            await self.websocket.send(json.dumps(message))
            self.log(f"📤 Sent: {text}")
            
        except Exception as e:
            self.log(f"❌ Failed to send message: {e}")
    
    async def listen_for_responses(self):
        """Listen for responses from the server"""
        if not self.connected or not self.websocket:
            return
        
        try:
            while True:
                response = await self.websocket.recv()
                response_data = json.loads(response)
                
                response_type = response_data.get("type")
                
                if response_type == "text":
                    text = response_data.get("data", "")
                    print(f"🤖 AI: {text}", end="", flush=True)
                    
                elif response_type == "turn_complete":
                    print()  # New line after complete response
                    self.log("✅ Turn complete")
                    
                elif response_type == "interrupted":
                    print()
                    self.log(f"⏸️ Interrupted: {response_data.get('data', '')}")
                    
                elif response_type == "error":
                    self.log(f"❌ Error: {response_data.get('data', 'Unknown error')}")
                    
                elif response_type == "session_id":
                    self.log(f"🆔 Session ID: {response_data.get('data', '')}")
                    
                else:
                    self.log(f"📥 Other message: {response_data}")
                    
        except websockets.exceptions.ConnectionClosed:
            self.log("🔌 Connection closed by server")
            self.connected = False
        except Exception as e:
            self.log(f"❌ Error receiving messages: {e}")
            self.connected = False
    
    async def close(self):
        """Close the connection"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            self.log("🔌 Connection closed")

async def run_quick_test():
    """Run a quick automated test"""
    client = SimpleClient()
    
    print("🚀 Running Quick Test")
    print("=" * 50)
    
    # Connect
    if not await client.connect():
        return
    
    # Test messages
    test_messages = [
        "Hi there!",
        "How is my wedding planning going?",
        "What's my budget status?",
        "Any overdue tasks I should know about?",
        "Show me vendor recommendations for photography"
    ]
    
    try:
        # Start listening for responses
        listen_task = asyncio.create_task(client.listen_for_responses())
        
        # Send test messages with delays
        for i, message in enumerate(test_messages, 1):
            print(f"\n--- Test {i}/{len(test_messages)} ---")
            await client.send_message(message)
            await asyncio.sleep(3)  # Wait 3 seconds between messages
        
        # Wait a bit more for final responses
        await asyncio.sleep(5)
        
        # Cancel listening task
        listen_task.cancel()
        
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    finally:
        await client.close()

async def run_interactive_chat():
    """Run interactive chat session"""
    client = SimpleClient()
    
    print("💬 Interactive Chat Mode")
    print("=" * 50)
    print("Type your messages and press Enter. Type 'quit' to exit.")
    print("=" * 50)
    
    # Connect
    if not await client.connect():
        return
    
    try:
        # Start listening for responses
        listen_task = asyncio.create_task(client.listen_for_responses())
        
        # Handle user input
        while client.connected:
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, input, "\n👤 You: "
                )
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                
                if user_input.strip():
                    await client.send_message(user_input)
                
            except (EOFError, KeyboardInterrupt):
                break
        
        # Cancel listening task
        listen_task.cancel()
        
    except Exception as e:
        print(f"❌ Chat session error: {e}")
    finally:
        await client.close()

def main():
    print("🎯 Sanskara AI Simple Test Client")
    print("Select test mode:")
    print("1. Quick automated test")
    print("2. Interactive chat")
    print("3. Exit")
    
    try:
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == "1":
            asyncio.run(run_quick_test())
        elif choice == "2":
            asyncio.run(run_interactive_chat())
        elif choice == "3":
            print("👋 Goodbye!")
            sys.exit(0)
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")
            return main()
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Simple Manual Test Client for Sanskara AI
Quick and easy testing of the WebSocket functionality
Updated to handle new 'session' message providing session_id for artifact operations.
"""

import asyncio
import websockets
import json
import sys
from datetime import datetime
import os
import mimetypes
import uuid
import pathlib
import requests

# Configuration
WS_URL = "ws://localhost:8765/ws"
API_BASE = "http://localhost:8765"  # REST API base for artifacts
USER_ID = "fca04215-2af3-4a4e-bcfa-c27a4f54474c"

class SimpleClient:
    def __init__(self, mode: str = "live"):
        self.websocket = None
        self.connected = False
        self.session_id = None  # ADK session id provided by server
        self._listener_task = None
        self._reconnector_task = None
        self.mode = mode # Store the mode
        # Reconnect policy
        self._max_reconnect_attempts = None  # None = unlimited attempts
        self._base_delay = 0.75  # seconds
    
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    async def connect(self):
        """Connect to the WebSocket server and complete handshake (ready + optional session)."""
        try:
            # Pass the mode as a query parameter
            ws_url_with_params = f"{WS_URL}?user_id={USER_ID}&mode={self.mode}"
            self.log(f"Connecting to {ws_url_with_params}")
            self.websocket = await websockets.connect(ws_url_with_params)
            # Loop until we receive 'ready'. Capture any 'session' message before/after.
            while True:
                msg = await self.websocket.recv()
                try:
                    data = json.loads(msg)
                except Exception:
                    data = {}
                mtype = data.get("type")
                if mtype == "session":
                    self.session_id = data.get("session_id") or data.get("data")
                    self.log(f"🆔 Session established: {self.session_id}")
                elif mtype == "ready":
                    self.connected = True
                    if not self.session_id:
                        self.log("⚠️ Ready received but no session id yet (server may have failed before sending session message)")
                    self.log("✅ Connected (ready received).")
                    break
                else:
                    self.log(f"📥 Pre-ready message: {data}")
            return True
        except Exception as e:
            self.log(f"❌ Connection failed: {e}")
            return False
    async def connect_with_retries(self, max_attempts: int | None = None) -> bool:
        """Try connect() with exponential backoff; max_attempts=None means unlimited."""
        attempt = 0
        while True:
            ok = await self.connect()
            if ok:
                return True
            attempt += 1
            if max_attempts is not None and attempt >= max_attempts:
                return False
            delay = self._base_delay * (2 ** (attempt - 1))
            self.log(f"⏳ Reconnect attempt {attempt} failed; retrying in {delay:.2f}s…")
            await asyncio.sleep(delay)

    async def ensure_connected(self) -> bool:
        if self.connected and self.websocket:
            return True
        self.log("Attempting to (re)connect…")
        return await self.connect_with_retries(self._max_reconnect_attempts)


    def start_listener(self):
        if self._listener_task is None or self._listener_task.done():
            self._listener_task = asyncio.create_task(self.listen_for_responses(), name="ws-listener")

    def start_reconnector(self):
        if self._reconnector_task is None or self._reconnector_task.done():
            self._reconnector_task = asyncio.create_task(self._reconnect_loop(), name="ws-reconnector")

    async def _reconnect_loop(self):
        """Background task to keep connection alive and restart listener on reconnect."""
        while True:
            try:
                if not self.connected:
                    ok = await self.ensure_connected()
                    if ok:
                        self.log("🔁 Reconnected.")
                        self.start_listener()
                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log(f"Reconnector error: {e}")
                await asyncio.sleep(2.0)
    
    async def send_message(self, text: str):
        """Send a text chat message."""
        if not self.connected or not self.websocket:
            self.log("❌ Not connected!")
            return
        try:
            await self.websocket.send(json.dumps({"type": "text", "data": text}))
            self.log(f"📤 Sent: {text}")
        except Exception as e:
            self.log(f"❌ Failed to send message: {e}")
    
    async def listen_for_responses(self):
        """Listen for responses from the server (runs until connection closes)."""
        if not self.connected or not self.websocket:
            return
        try:
            while True:
                response = await self.websocket.recv()
                try:
                    data = json.loads(response)
                except Exception:
                    self.log(f"📥 Non-JSON message: {response}")
                    continue
                rtype = data.get("type")
                if rtype == "text":
                    text = data.get("data", "")
                    print(f"🤖 AI: {text}", end="", flush=True)
                elif rtype == "turn_complete":
                    print()
                    self.log("✅ Turn complete")
                elif rtype == "interrupted":
                    print()
                    self.log(f"⏸️ Interrupted: {data.get('data', '')}")
                elif rtype == "error":
                    self.log(f"❌ Error: {data.get('data', 'Unknown error')}")
                elif rtype == "reconnecting":
                    info = data.get("data", {})
                    self.log(f"🔁 Server reconnecting upstream (attempt {info.get('attempt')} | retry_in {info.get('retry_in')}s)")
                elif rtype == "session":
                    self.session_id = data.get("session_id") or data.get("data")
                    self.log(f"🆔 Session updated: {self.session_id}")
                elif rtype == "session_id":  # legacy
                    self.session_id = data.get("data")
                    self.log(f"🆔 (legacy) Session ID: {self.session_id}")
                else:
                    self.log(f"📥 Other message: {data}")
        except websockets.exceptions.ConnectionClosedOK:
            self.log("🔌 Connection closed gracefully by server")
            self.connected = False
        except websockets.exceptions.ConnectionClosed as e:
            self.log(f"🔌 Connection closed unexpectedly by server: code={e.code}, reason={e.reason}")
            self.connected = False
        except Exception as e:
            self.log(f"❌ Error receiving messages: {e}")
            self.connected = False
    
    async def close(self):
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            self.log("🔌 Connection closed")
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
        if self._reconnector_task and not self._reconnector_task.done():
            self._reconnector_task.cancel()
    
    # ---------------- Artifact helper methods (REST) -----------------
    def upload_artifact(self, file_path: str, caption: str = None):
        """Synchronous helper to upload an artifact via REST. Requires session_id."""
        if not self.session_id:
            self.log("❌ No session_id yet. Cannot upload.")
            return
        path = pathlib.Path(file_path)
        if not path.exists():
            self.log(f"❌ File not found: {file_path}")
            return
        url = f"{API_BASE}/artifacts/upload"
        mime, _ = mimetypes.guess_type(str(path))
        files = {"file": (path.name, path.read_bytes(), mime or "application/octet-stream")}
        data = {"user_id": USER_ID, "session_id": self.session_id}
        if caption:
            data["caption"] = caption
        try:
            resp = requests.post(url, files=files, data=data, timeout=60)
            if resp.ok:
                js = resp.json()
                version = js.get("artifact", {}).get("version")
                self.log(f"📦 Uploaded artifact: {path.name} version={version}")
            else:
                self.log(f"❌ Upload failed {resp.status_code}: {resp.text}")
        except Exception as e:
            self.log(f"❌ Upload exception: {e}")
    
    def list_artifacts(self):
        if not self.session_id:
            self.log("❌ No session_id yet. Cannot list.")
            return
        url = f"{API_BASE}/artifacts/list"
        params = {"user_id": USER_ID, "session_id": self.session_id}
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.ok:
                js = resp.json()
                arts = js.get("artifacts", [])
                if not arts:
                    self.log("📭 No artifacts.")
                else:
                    self.log("📂 Artifacts:")
                    for a in arts:
                        self.log(f"  - {a.get('filename')} (version={a.get('version')}, mime={a.get('mime_type')})")
            else:
                self.log(f"❌ List failed {resp.status_code}: {resp.text}")
        except Exception as e:
            self.log(f"❌ List exception: {e}")

    def fetch_artifact_content(self, version: str):
        if not self.session_id:
            self.log("❌ No session_id yet. Cannot fetch content.")
            return
        url = f"{API_BASE}/artifacts/content"
        params = {"user_id": USER_ID, "session_id": self.session_id, "version": version}
        try:
            resp = requests.get(url, params=params, timeout=60)
            if resp.ok:
                js = resp.json().get("artifact", {})
                size = len(js.get("base64_content") or "")
                self.log(f"🧾 Content fetched for version={version} base64_len={size}")
            else:
                self.log(f"❌ Content fetch failed {resp.status_code}: {resp.text}")
        except Exception as e:
            self.log(f"❌ Content fetch exception: {e}")


async def run_quick_test(mode: str):
    client = SimpleClient(mode=mode)
    print(f"🚀 Running Quick Test in {mode.upper()} mode")
    print("=" * 50)
    if not await client.ensure_connected():
        return
    client.start_listener()
    # In normal mode, we don't need the reconnector task as it's not streaming
    if mode == "live":
        client.start_reconnector()
    # Wait a moment to ensure session id captured
    await asyncio.sleep(1)
    # Optional: list artifacts initially
    client.list_artifacts()
    test_messages = [
        "Hi there!",
        "How is my wedding planning going?",
        "What's my budget status?",
        "Any overdue tasks I should know about?",
        "Show me vendor recommendations for photography"
    ]
    try:
        for i, msg in enumerate(test_messages, 1):
            print(f"\n--- Test {i}/{len(test_messages)} ---")
            await client.send_message(msg)
            # In normal mode, we expect a complete response, so no need for sleep between messages
            if mode == "live":
                await asyncio.sleep(3)
        if mode == "live":
            await asyncio.sleep(5)
    finally:
        await client.close()

async def run_interactive_chat(mode: str):
    client = SimpleClient(mode=mode)
    print(f"💬 Interactive Chat Mode in {mode.upper()} mode")
    print("=" * 50)
    print("Commands: /upload <path> [caption...] | /list | /content <version> | /session | /quit")
    if not await client.ensure_connected():
        return
    client.start_listener()
    # In normal mode, we don't need the reconnector task as it's not streaming
    if mode == "live":
        client.start_reconnector()
    loop = asyncio.get_event_loop()
    try:
        while client.connected:
            try:
                raw = await loop.run_in_executor(None, input, "\n👤 You: ")
            except (EOFError, KeyboardInterrupt):
                break
            if not raw:
                continue
            if raw.lower() in {"/quit", "/exit", "quit", "exit", "q"}:
                break
            if raw.startswith("/session"):
                client.log(f"Current session_id: {client.session_id}")
                continue
            if raw.startswith("/upload"):
                parts = raw.split()
                if len(parts) < 2:
                    client.log("Usage: /upload <file_path> [caption...]")
                    continue
                file_path = parts[1]
                caption = " ".join(parts[2:]) if len(parts) > 2 else None
                client.upload_artifact(file_path, caption)
                continue
            if raw.startswith("/list"):
                client.list_artifacts()
                continue
            if raw.startswith("/content"):
                parts = raw.split()
                if len(parts) != 2:
                    client.log("Usage: /content <version>")
                    continue
                client.fetch_artifact_content(parts[1])
                continue
            # Normal chat (ensure connected before send)
            if await client.ensure_connected():
                await client.send_message(raw)
            else:
                client.log("❌ Unable to send; still reconnecting. Please try again.")
    finally:
        await client.close()

# ---------------- Entry Point ----------------

def main():
    print("🎯 Sanskara AI Simple Test Client")
    
    # Prompt for mode selection
    while True:
        print("\nSelect mode:")
        print("1. Live (streaming, real-time interaction)")
        print("2. Normal (request-response, non-streaming)")
        mode_choice = input("Enter mode choice (1-2): ").strip()
        if mode_choice == "1":
            selected_mode = "live"
            break
        elif mode_choice == "2":
            selected_mode = "normal"
            break
        else:
            print("❌ Invalid mode choice. Please enter 1 or 2.")

    print("\nSelect test type:")
    print("1. Quick automated test")
    print("2. Interactive chat")
    print("3. Exit")
    try:
        test_choice = input("\nEnter test choice (1-3): ").strip()
        if test_choice == "1":
            asyncio.run(run_quick_test(mode=selected_mode))
        elif test_choice == "2":
            asyncio.run(run_interactive_chat(mode=selected_mode))
        elif test_choice == "3":
            print("👋 Goodbye!")
            sys.exit(0)
        else:
            print("❌ Invalid test choice. Please enter 1, 2, or 3.")
            return main()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

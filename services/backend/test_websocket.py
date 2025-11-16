#!/usr/bin/env python3
"""
WebSocket Test Script - CLI Tool

This is a testing/debugging tool for WebSocket connections.
Safe to commit to git and share with team.

Usage:
    python test_websocket.py

Features:
    - Interactive prompts for token and project_id
    - Real-time message display
    - Automatic timeout handling
    - Error reporting

Requirements:
    pip install websockets

See also:
    - test_websocket.html (UI version)
    - docs/WEBSOCKET_TESTING.md (full guide)
"""
import asyncio
import websockets
import json
import sys

async def test_websocket():
    # Get credentials from user
    print("🔧 WebSocket Test Script")
    print("=" * 60)
    
    token = input("Enter your JWT token (from /api/v1/login/access-token): ").strip()
    project_id = input("Enter project ID: ").strip()
    
    if not token or not project_id:
        print("❌ Token and project_id are required!")
        return
    
    uri = f"ws://localhost:8000/api/v1/chat/ws?project_id={project_id}&token={token}"
    
    print(f"\n📡 Connecting to: {uri}")
    print("=" * 60)
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected!")
            
            # Receive connection confirmation
            response = await websocket.recv()
            data = json.loads(response)
            print(f"📨 {data['type']}: {data.get('message', data)}")
            
            # Send a test message
            test_message = {
                "type": "message",
                "content": "Tôi muốn tạo một trang web bán hàng online",
                "author_type": "user"
            }
            
            print(f"\n📤 Sending: {test_message['content']}")
            await websocket.send(json.dumps(test_message))
            
            print("\n📨 Waiting for responses...")
            print("=" * 60)
            
            # Receive responses
            message_count = 0
            while message_count < 10:  # Limit to 10 messages for testing
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                    data = json.loads(response)
                    message_count += 1
                    
                    if data['type'] == 'typing':
                        status = "typing..." if data.get('is_typing') else "stopped typing"
                        print(f"⌨️  {data.get('agent_name', 'Agent')} is {status}")
                    
                    elif data['type'] in ['message', 'agent_message']:
                        msg_data = data.get('data', {})
                        content = msg_data.get('content', '')
                        author = msg_data.get('author_type', 'unknown')
                        print(f"\n💬 [{author}]: {content[:200]}...")
                        
                        # If this is the final agent response, we can stop
                        if 'sprint_plan' in content.lower() or 'generated' in content.lower():
                            print("\n✅ Received agent response!")
                            break
                    
                    elif data['type'] == 'pong':
                        print("🏓 Pong received")
                    
                    else:
                        print(f"📨 {data['type']}: {data}")
                
                except asyncio.TimeoutError:
                    print("\n⏱️  Timeout waiting for response")
                    break
                except websockets.exceptions.ConnectionClosed:
                    print("\n🔌 Connection closed by server")
                    break
            
            print("\n" + "=" * 60)
            print("✅ Test completed!")
            
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Connection failed: {e}")
        print("   Check your token and project_id")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(test_websocket())
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
        sys.exit(0)

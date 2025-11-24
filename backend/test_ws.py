"""
Test WebSocket connection directly
"""
import asyncio
import websockets
import json

async def test_websocket():
    # Replace with your actual project_id and token
    project_id = "b86274d9-ac6d-4eb6-8810-8aa8220c1b0e"
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0NDM3NDhkOS0yMmU4LTRhOTMtOWM4Yi00MGUwODI3MTkyNTkiLCJleHAiOjE3NjQ2NzY2MjYsImlhdCI6MTc2Mzk4NTQyNiwibmJmIjoxNzYzOTg1NDI2LCJ0eXBlIjoiYWNjZXNzIiwianRpIjoibE5WSE0xa3BJZnBpZmVzVnNTZlZnQSJ9.RpAk8BEDw8XMl_j8YBQGcLbXPwZwW5oW_mwIbgImr8U"
    
    url = f"ws://localhost:8000/api/v1/chat/ws?project_id={project_id}&token={token}"
    
    print(f"[*] Connecting to: {url}")
    
    try:
        async with websockets.connect(url) as websocket:
            print("[+] Connected!")
            
            # Wait for connection confirmation
            message = await websocket.recv()
            data = json.loads(message)
            print(f"[<] Received: {data}")
            
            # Send a test message
            test_msg = {
                "type": "message",
                "content": "Hello from test script!",
                "project_id": project_id
            }
            await websocket.send(json.dumps(test_msg))
            print(f"[>] Sent: {test_msg}")
            
            # Wait for response
            response = await websocket.recv()
            print(f"[<] Response: {json.loads(response)}")
            
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"[-] Connection failed with status: {e.status_code}")
        print(f"    Headers: {e.headers}")
    except Exception as e:
        print(f"[-] Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())

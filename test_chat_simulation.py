#!/usr/bin/env python3
"""
Chat Simulation Test - Simulate user chatting with AI agents
Test entire flow: User chat -> Agent processing -> Approval -> Story creation
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
import websockets

# Configuration
BASE_URL = "http://localhost:8001/api/v1"
WS_URL = "ws://localhost:8001/api/v1/chat/ws"

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
RESET = "\033[0m"


class ChatSimulator:
    """Simulate a user chatting with AI agents"""

    def __init__(self):
        self.token: Optional[str] = None
        self.project_id: Optional[str] = None
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.pending_approvals = []

    def print_user(self, message: str):
        """Print user message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{CYAN}[{timestamp}] User: {message}{RESET}")

    def print_agent(self, agent_name: str, message: str):
        """Print agent message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{MAGENTA}[{timestamp}] Agent {agent_name}: {message}{RESET}")

    def print_system(self, message: str):
        """Print system message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{BLUE}[{timestamp}] System: {message}{RESET}")

    def print_success(self, message: str):
        """Print success message"""
        print(f"{GREEN}[SUCCESS] {message}{RESET}")

    def print_error(self, message: str):
        """Print error message"""
        print(f"{RED}[ERROR] {message}{RESET}")

    def print_warning(self, message: str):
        """Print warning message"""
        print(f"{YELLOW}[WARNING] {message}{RESET}")

    def load_credentials(self) -> bool:
        """Load token and project_id from test_data.json"""
        try:
            if Path("test_data.json").exists():
                with open("test_data.json", "r") as f:
                    data = json.load(f)
                    self.token = data.get("token")
                    self.project_id = data.get("project_id")

                if self.token and self.project_id:
                    self.print_success("Loaded credentials from test_data.json")
                    return True
        except Exception as e:
            self.print_warning(f"Could not load test_data.json: {e}")

        return False

    def login(self, email: str = "admin@gmail.com", password: str = "admin") -> bool:
        """Login and get token"""
        try:
            self.print_system("Logging in...")
            response = requests.post(
                f"{BASE_URL}/login",
                json={
                    "email": email,
                    "password": password,
                    "login_provider": False,
                    "fullname": ""
                },
            )
            response.raise_for_status()
            token_data = response.json()
            self.token = token_data["access_token"]
            self.print_success(f"Logged in as {email}")
            return True
        except requests.exceptions.HTTPError as e:
            self.print_error(f"Login failed: HTTP {e.response.status_code}")
            self.print_error(f"Response: {e.response.text}")
            return False
        except Exception as e:
            self.print_error(f"Login failed: {e}")
            return False

    def get_project(self) -> bool:
        """Get or create project"""
        headers = {"Authorization": f"Bearer {self.token}"}

        try:
            # Try to get existing project
            self.print_system("Getting project...")
            response = requests.get(f"{BASE_URL}/projects/", headers=headers)
            response.raise_for_status()
            projects = response.json().get("data", [])

            if projects:
                self.project_id = projects[0]["id"]
                self.print_success(f"Using project: {projects[0]['name']}")
                return True
            else:
                # Create new project
                self.print_system("Creating new project...")
                response = requests.post(
                    f"{BASE_URL}/projects/",
                    headers=headers,
                    json={
                        "name": "Chat Test Project",
                        "code": "CHAT",
                        "tech_stack": "nodejs-react",
                    },
                )
                response.raise_for_status()
                project = response.json()
                self.project_id = project["id"]
                self.print_success(f"Created project: {project['name']}")
                return True
        except Exception as e:
            self.print_error(f"Failed to get/create project: {e}")
            return False

    async def connect_websocket(self):
        """Connect to WebSocket"""
        try:
            ws_url = f"{WS_URL}?project_id={self.project_id}&token={self.token}"
            self.print_system("Connecting to WebSocket...")
            self.websocket = await websockets.connect(ws_url)
            self.print_success("WebSocket connected!")
        except Exception as e:
            self.print_error(f"WebSocket connection failed: {e}")
            raise

    async def listen_to_events(self):
        """Listen to WebSocket events"""
        try:
            while True:
                message = await self.websocket.recv()
                data = json.loads(message)
                await self.handle_ws_event(data)
        except websockets.exceptions.ConnectionClosed:
            self.print_warning("WebSocket connection closed")
        except Exception as e:
            self.print_error(f"WebSocket error: {e}")

    async def handle_ws_event(self, event: dict):
        """Handle WebSocket events"""
        event_type = event.get("type")

        if event_type == "agent_message":
            agent_name = event.get("agent_name", "Agent")
            content = event.get("content", "")
            self.print_agent(agent_name, content)

        elif event_type == "routing":
            from_agent = event.get("from_agent", "")
            to_agent = event.get("to_agent", "")
            reason = event.get("reason", "")
            self.print_system(f"Routing: {from_agent} -> {to_agent} ({reason})")

        elif event_type == "approval_request":
            approval_id = event.get("approval_request_id")
            proposed_data = event.get("proposed_data", {})
            preview_data = event.get("preview_data", {})

            self.print_system("=" * 60)
            self.print_system("APPROVAL REQUEST RECEIVED")
            self.print_system("=" * 60)

            title = proposed_data.get("title", "N/A")
            description = proposed_data.get("description", "N/A")
            story_point = proposed_data.get("story_point", "N/A")
            story_type = proposed_data.get("story_type", "UserStory")

            print(f"\n{YELLOW}Title:{RESET} {title}")
            print(f"{YELLOW}Type:{RESET} {story_type}")
            print(f"{YELLOW}Story Points:{RESET} {story_point}")
            print(f"{YELLOW}Description:{RESET}")
            print(f"  {description[:200]}{'...' if len(description) > 200 else ''}\n")

            # Add to pending approvals
            self.pending_approvals.append({
                "id": approval_id,
                "title": title,
                "proposed_data": proposed_data
            })

            self.print_system(f"Approval ID: {approval_id}")
            self.print_warning("Waiting for your decision...")

        elif event_type == "kanban_update":
            action = event.get("action", "")
            story_id = event.get("story_id", "")
            title = event.get("title", "")
            status = event.get("status", "")

            self.print_success(f"Kanban Update: {action} - {title} [{status}]")
            self.print_system(f"Story ID: {story_id}")

        elif event_type == "flow_completed":
            flow_type = event.get("flow_type", "")
            status = event.get("status", "")
            self.print_success(f"Flow completed: {flow_type} ({status})")

        else:
            self.print_system(f"Event: {event_type}")

    async def send_message(self, message: str):
        """Send message to AI agents"""
        headers = {"Authorization": f"Bearer {self.token}"}

        self.print_user(message)

        try:
            response = requests.post(
                f"{BASE_URL}/workflows/process-message",
                headers=headers,
                json={
                    "project_id": self.project_id,
                    "content": message,
                    "message_type": "text",
                },
                timeout=120,
            )
            response.raise_for_status()
            result = response.json()

            self.print_system(f"Message sent! Execution ID: {result['execution_id']}")
            return result
        except requests.exceptions.Timeout:
            self.print_error("Request timed out - check OPENAI_API_KEY")
            return None
        except Exception as e:
            self.print_error(f"Failed to send message: {e}")
            return None

    def approve_story(self, approval_id: str, approved: bool = True, feedback: str = ""):
        """Approve or reject story"""
        headers = {"Authorization": f"Bearer {self.token}"}

        try:
            decision = "APPROVE" if approved else "REJECT"
            self.print_user(f"{decision} - {feedback if feedback else 'OK'}")

            response = requests.post(
                f"{BASE_URL}/workflows/approve/{approval_id}",
                headers=headers,
                json={
                    "approved": approved,
                    "feedback": feedback or ("Approved!" if approved else "Rejected"),
                },
            )
            response.raise_for_status()
            result = response.json()

            if approved and result.get("created_entity_id"):
                self.print_success(f"Story created! ID: {result['created_entity_id']}")
            elif approved:
                self.print_success("Approved successfully")
            else:
                self.print_warning("Rejected successfully")

            # Remove from pending
            self.pending_approvals = [
                a for a in self.pending_approvals if a["id"] != approval_id
            ]

            return result
        except Exception as e:
            self.print_error(f"Failed to approve: {e}")
            return None

    def list_pending_approvals(self):
        """List pending approvals"""
        if not self.pending_approvals:
            self.print_warning("No pending approvals")
            return

        print(f"\n{YELLOW}{'='*60}{RESET}")
        print(f"{YELLOW}PENDING APPROVALS{RESET}")
        print(f"{YELLOW}{'='*60}{RESET}\n")

        for i, approval in enumerate(self.pending_approvals, 1):
            print(f"{i}. {approval['title']}")
            print(f"   ID: {approval['id']}\n")

    async def interactive_mode(self):
        """Interactive chat mode"""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}INTERACTIVE CHAT MODE{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")

        print("Commands:")
        print("  - Type your message to send to AI agents")
        print("  - /approve <number> - Approve pending request")
        print("  - /reject <number> - Reject pending request")
        print("  - /list - List pending approvals")
        print("  - /quit - Exit\n")

        # Start WebSocket listener in background
        listener_task = asyncio.create_task(self.listen_to_events())

        try:
            while True:
                try:
                    # Get user input (run in executor to not block asyncio)
                    user_input = await asyncio.get_event_loop().run_in_executor(
                        None, input, f"{CYAN}You > {RESET}"
                    )

                    if not user_input.strip():
                        continue

                    # Handle commands
                    if user_input.startswith("/"):
                        parts = user_input.split()
                        command = parts[0].lower()

                        if command == "/quit":
                            self.print_system("Goodbye!")
                            break

                        elif command == "/list":
                            self.list_pending_approvals()

                        elif command == "/approve":
                            if len(parts) < 2:
                                self.print_error("Usage: /approve <number>")
                                continue

                            try:
                                idx = int(parts[1]) - 1
                                if 0 <= idx < len(self.pending_approvals):
                                    approval = self.pending_approvals[idx]
                                    feedback = " ".join(parts[2:]) if len(parts) > 2 else ""
                                    self.approve_story(approval["id"], True, feedback)
                                else:
                                    self.print_error("Invalid approval number")
                            except ValueError:
                                self.print_error("Invalid number")

                        elif command == "/reject":
                            if len(parts) < 2:
                                self.print_error("Usage: /reject <number> [reason]")
                                continue

                            try:
                                idx = int(parts[1]) - 1
                                if 0 <= idx < len(self.pending_approvals):
                                    approval = self.pending_approvals[idx]
                                    reason = " ".join(parts[2:]) if len(parts) > 2 else "Rejected"
                                    self.approve_story(approval["id"], False, reason)
                                else:
                                    self.print_error("Invalid approval number")
                            except ValueError:
                                self.print_error("Invalid number")

                        else:
                            self.print_error(f"Unknown command: {command}")

                    else:
                        # Send message to agents
                        await self.send_message(user_input)

                except EOFError:
                    break
                except KeyboardInterrupt:
                    break

        finally:
            listener_task.cancel()
            try:
                await listener_task
            except asyncio.CancelledError:
                pass


async def run_simulation():
    """Run chat simulation"""
    simulator = ChatSimulator()

    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}VibeSDLC Chat Simulation{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

    # Step 1: Load credentials or login
    if not simulator.load_credentials():
        if not simulator.login():
            return

    # Step 2: Get/create project
    if not simulator.get_project():
        return

    # Save credentials for next time
    with open("test_data.json", "w") as f:
        json.dump({
            "token": simulator.token,
            "project_id": simulator.project_id
        }, f, indent=2)

    # Step 3: Connect WebSocket
    await simulator.connect_websocket()

    # Step 4: Interactive mode
    await simulator.interactive_mode()

    # Cleanup
    if simulator.websocket:
        await simulator.websocket.close()


def main():
    """Main entry point"""
    try:
        asyncio.run(run_simulation())
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Interrupted by user{RESET}")
    except Exception as e:
        print(f"\n{RED}Error: {e}{RESET}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

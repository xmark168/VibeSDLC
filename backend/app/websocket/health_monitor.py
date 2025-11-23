"""
WebSocket Health Monitor

Monitors WebSocket connection health with ping/pong mechanism
and automatically disconnects dead connections.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import UUID

from fastapi import WebSocket


logger = logging.getLogger(__name__)


@dataclass
class ConnectionHealth:
    """Health information for a WebSocket connection."""
    
    websocket: WebSocket
    project_id: UUID
    user_id: UUID
    last_pong: datetime
    missed_pongs: int = 0
    is_monitoring: bool = True


class WebSocketHealthMonitor:
    """
    Monitor WebSocket connection health and auto-heal.
    
    Features:
    - Periodic ping/pong health checks
    - Auto-disconnect dead connections
    - Connection statistics tracking
    """
    
    def __init__(self, ping_interval: int = 30, max_missed_pongs: int = 3):
        """
        Initialize health monitor.
        
        Args:
            ping_interval: Seconds between ping messages (default: 30)
            max_missed_pongs: Max missed pongs before disconnect (default: 3)
        """
        self.ping_interval = ping_interval
        self.max_missed_pongs = max_missed_pongs
        
        # Track connection health by websocket ID
        self.connections: Dict[int, ConnectionHealth] = {}
        
        # Statistics
        self.total_monitored = 0
        self.total_disconnected = 0
    
    async def start_monitoring(
        self,
        websocket: WebSocket,
        project_id: UUID,
        user_id: UUID
    ) -> None:
        """
        Start monitoring a WebSocket connection.
        
        Args:
            websocket: WebSocket connection to monitor
            project_id: Project the connection belongs to
            user_id: User ID for the connection
        """
        ws_id = id(websocket)
        
        # Create health record
        health = ConnectionHealth(
            websocket=websocket,
            project_id=project_id,
            user_id=user_id,
            last_pong=datetime.now(timezone.utc),
            missed_pongs=0,
            is_monitoring=True
        )
        
        self.connections[ws_id] = health
        self.total_monitored += 1
        
        logger.info(
            f"Started monitoring WebSocket {ws_id} "
            f"(user={user_id}, project={project_id})"
        )
        
        # Start ping loop in background
        asyncio.create_task(self._ping_loop(health))
    
    def stop_monitoring(self, websocket: WebSocket) -> None:
        """
        Stop monitoring a WebSocket connection.
        
        Args:
            websocket: WebSocket to stop monitoring
        """
        ws_id = id(websocket)
        
        if ws_id in self.connections:
            health = self.connections[ws_id]
            health.is_monitoring = False
            del self.connections[ws_id]
            
            logger.info(f"Stopped monitoring WebSocket {ws_id}")
    
    def record_pong(self, websocket: WebSocket) -> None:
        """
        Record pong received from client.
        
        Args:
            websocket: WebSocket that sent pong
        """
        ws_id = id(websocket)
        
        if ws_id in self.connections:
            health = self.connections[ws_id]
            health.last_pong = datetime.now(timezone.utc)
            health.missed_pongs = 0
            
            logger.debug(f"Pong received from WebSocket {ws_id}")
    
    async def _ping_loop(self, health: ConnectionHealth) -> None:
        """
        Periodic ping loop for a connection.
        
        Sends ping every ping_interval seconds and checks for pong responses.
        Disconnects if too many pongs are missed.
        
        Args:
            health: ConnectionHealth to monitor
        """
        ws_id = id(health.websocket)
        
        try:
            while health.is_monitoring:
                await asyncio.sleep(self.ping_interval)
                
                # Check if still monitoring (might have been stopped)
                if not health.is_monitoring:
                    break
                
                try:
                    # Send ping
                    await health.websocket.send_json({"type": "ping"})
                    logger.debug(f"Sent ping to WebSocket {ws_id}")
                    
                    # Wait a bit for pong response
                    await asyncio.sleep(5)
                    
                    # Check if pong was received recently
                    time_since_pong = (
                        datetime.now(timezone.utc) - health.last_pong
                    ).total_seconds()
                    
                    if time_since_pong > self.ping_interval + 10:
                        # No recent pong, increment missed count
                        health.missed_pongs += 1
                        
                        # Only log warning if getting critical (last chance)
                        if health.missed_pongs >= self.max_missed_pongs - 1:
                            logger.warning(
                                f"WebSocket {ws_id} missed pong "
                                f"({health.missed_pongs}/{self.max_missed_pongs})"
                            )
                        
                        if health.missed_pongs >= self.max_missed_pongs:
                            # Connection is dead, close it
                            logger.error(
                                f"WebSocket {ws_id} is dead "
                                f"(missed {health.missed_pongs} pongs), closing..."
                            )
                            
                            await health.websocket.close(
                                code=1008,
                                reason="Connection health check failed"
                            )
                            
                            self.total_disconnected += 1
                            health.is_monitoring = False
                            
                            # Clean up
                            if ws_id in self.connections:
                                del self.connections[ws_id]
                            
                            break
                    
                except Exception as e:
                    logger.error(f"Error sending ping to WebSocket {ws_id}: {e}")
                    # Connection might be dead, stop monitoring
                    health.is_monitoring = False
                    if ws_id in self.connections:
                        del self.connections[ws_id]
                    break
        
        except asyncio.CancelledError:
            logger.info(f"Ping loop cancelled for WebSocket {ws_id}")
            health.is_monitoring = False
        
        except Exception as e:
            logger.error(f"Error in ping loop for WebSocket {ws_id}: {e}")
            health.is_monitoring = False
    
    def get_connection_health(self, websocket: WebSocket) -> Optional[ConnectionHealth]:
        """
        Get health information for a connection.
        
        Args:
            websocket: WebSocket to get health for
            
        Returns:
            ConnectionHealth if found, None otherwise
        """
        ws_id = id(websocket)
        return self.connections.get(ws_id)
    
    def get_statistics(self) -> dict:
        """
        Get health monitor statistics.
        
        Returns:
            Dictionary with statistics
        """
        active_connections = len(self.connections)
        
        return {
            "active_connections": active_connections,
            "total_monitored": self.total_monitored,
            "total_disconnected": self.total_disconnected,
            "ping_interval": self.ping_interval,
            "max_missed_pongs": self.max_missed_pongs,
        }


# Global health monitor instance
health_monitor = WebSocketHealthMonitor()

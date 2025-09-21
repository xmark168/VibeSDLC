# aihub/agents/registry.py
from typing import Dict, Type
from .base_agent import BaseAgent

class AgentRegistry:
    """Quản lý và đăng ký các agents"""
    
    _agents: Dict[str, Type[BaseAgent]] = {}
    _instances: Dict[str, BaseAgent] = {}
    
    @classmethod
    def register(cls, name: str, agent_class: Type[BaseAgent]):
        """Đăng ký agent class"""
        cls._agents[name] = agent_class
    
    @classmethod
    def get_agent(cls, name: str, config: dict = None) -> BaseAgent:
        """Lấy instance của agent"""
        if name not in cls._instances:
            if name not in cls._agents:
                raise ValueError(f"Agent '{name}' không được đăng ký")
            
            agent_class = cls._agents[name]
            cls._instances[name] = agent_class(config or {})
        
        return cls._instances[name]
    
    @classmethod
    def list_agents(cls) -> list:
        """Liệt kê tất cả agents đã đăng ký"""
        return list(cls._agents.keys())

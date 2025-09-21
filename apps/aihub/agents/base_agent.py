import os

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from pydantic import BaseModel
import yaml

class AgentResponse(BaseModel):
    success: bool
    result: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}

class BaseAgent(ABC):
    """Base class cho tất cả AI agents"""
    
    def __init__(self, agent_name: str, custom_config: Dict[str, Any] = None):
        self.agent_name = agent_name
        self.config = self._load_config(custom_config)
        self.name = self.__class__.__name__
        self._initialized = False
    
    def _load_config(self, custom_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Load cấu hình từ file config của agent"""
        config_path = os.path.join(
            os.path.dirname(__file__), 
            self.agent_name, 
            'config.py'
        )
        
        # Load default config từ agent folder
        default_config = {}
        if os.path.exists(config_path):
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("config", config_path)
                config_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(config_module)
                default_config = getattr(config_module, 'DEFAULT_CONFIG', {})
            except Exception as e:
                print(f"Lỗi load config cho {self.agent_name}: {e}")
        
        # Merge với custom config
        if custom_config:
            default_config.update(custom_config)
        
        return default_config
    
    @abstractmethod
    async def process(self, input_data: Any) -> AgentResponse:
        """Xử lý input và trả về kết quả"""
        pass
    
    @abstractmethod
    def initialize(self) -> bool:
        """Khởi tạo agent"""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Trả về trạng thái của agent"""
        return {
            'agent_name': self.agent_name,
            'class_name': self.name,
            'config': self.config,
            'initialized': self._initialized,
            'capabilities': self.get_capabilities()
        }
    
    def get_capabilities(self) -> List[str]:
        """Trả về danh sách khả năng của agent"""
        return ['basic_processing']
    
    @classmethod
    def get_agent_info(cls) -> Dict[str, Any]:
        """Thông tin static về agent class"""
        return {
            'class_name': cls.__name__,
            'description': cls.__doc__ or 'No description available',
        }
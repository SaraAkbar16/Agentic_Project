from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseTool(ABC):
    """
    Base class for all MCP tools.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A description of what the tool does."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """Execute the tool's logic."""
        pass

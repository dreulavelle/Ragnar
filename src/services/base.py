import threading
from abc import ABC, abstractmethod
from typing import Optional

from ai.ollama_client import OllamaClient
from utils.logger import logger


class BaseService(threading.Thread, ABC):
    """Abstract base class for all services"""

    def __init__(self, name: str, ollama: Optional[OllamaClient] = None):
        super().__init__(name=name)
        self.initialized = False
        self.running = True
        self.ollama = ollama

        try:
            if self.setup():
                self.initialized = True
        except Exception as e:
            logger.exception(f"Failed to initialize {name} service: {e}")

    @abstractmethod
    def setup(self) -> bool:
        """Setup the service. Return True if successful."""
        raise NotImplementedError

    @abstractmethod
    def validate(self) -> bool:
        """Validate service configuration. Return True if valid."""
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        """Stop the service."""
        self.running = False
        self.join()

    @abstractmethod
    def run(self) -> None:
        """Run the service"""
        raise NotImplementedError

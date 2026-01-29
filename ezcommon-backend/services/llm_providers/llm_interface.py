"""Abstract base class for LLM providers"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class LLMProvider(ABC):
    """Abstract base class defining the interface for LLM providers"""
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the LLM provider"""
        pass
    
    @abstractmethod
    def chat_completion(self, 
                       messages: List[Dict[str, str]], 
                       model: Optional[str] = None,
                       temperature: float = 0.7,
                       max_tokens: int = 1024,
                       **kwargs) -> Dict[str, Any]:
        """
        Get chat completion from LLM
        
        Returns:
            {
                'content': str (the response text),
                'model': str
            }
        """
        pass
    
    @abstractmethod
    def transcribe_audio(self, 
                        audio_bytes: bytes,
                        language: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe audio to text
        
        Returns:
            {
                'text': str,
                'model': str
            }
        """
        pass
    
    @abstractmethod
    def vision_analysis(self, 
                       image_base64: str, 
                       prompt: str,
                       model: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze image with vision model
        
        Returns:
            {
                'content': str,
                'model': str
            }
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the LLM provider is available and configured"""
        pass
    
    @abstractmethod
    def get_provider_info(self) -> Dict[str, str]:
        """Get provider information"""
        pass

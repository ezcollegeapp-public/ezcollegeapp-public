"""OpenAI implementation of LLMProvider"""

import os
from typing import Dict, List, Any, Optional
from .llm_interface import LLMProvider

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class OpenAIProvider(LLMProvider):
    """OpenAI provider supporting GPT-4, GPT-4o, GPT-4o-mini, and Whisper"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize OpenAI provider
        
        Args:
            config: Configuration dictionary containing:
                - OPENAI_API_KEY: API key
                - OPENAI_MODEL: Default chat model (default: gpt-4o-mini)
                - OPENAI_VISION_MODEL: Vision model (default: gpt-4o)
                - OPENAI_TRANSCRIBE_MODEL: Transcription model (default: whisper-1)
        """
        if not HAS_OPENAI:
            raise ImportError("OpenAI SDK not installed. Install with: pip install openai")
        
        self.api_key = config.get('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not provided in config")
        
        self.client = OpenAI(api_key=self.api_key)
        self.chat_model = config.get('OPENAI_MODEL', 'gpt-4o-mini')
        self.vision_model = config.get('OPENAI_VISION_MODEL', 'gpt-4o')
        self.transcribe_model = config.get('OPENAI_TRANSCRIBE_MODEL', 'whisper-1')
        
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize OpenAI provider"""
        try:
            # Test connection
            self.client.models.list()
            self._initialized = True
            print(f"✓ OpenAI initialized (chat: {self.chat_model}, vision: {self.vision_model})")
            return True
        except Exception as e:
            print(f"⚠ OpenAI initialization failed: {e}")
            self._initialized = False
            return False
    
    def chat_completion(self, 
                       messages: List[Dict[str, str]], 
                       model: Optional[str] = None,
                       temperature: float = 0.7,
                       max_tokens: int = 1024,
                       **kwargs) -> Dict[str, Any]:
        """Get chat completion from OpenAI"""
        if not self._initialized:
            raise RuntimeError("OpenAI provider not initialized")
        
        model = model or self.chat_model
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            return {
                'content': response.choices[0].message.content,
                'model': model
            }
        except Exception as e:
            print(f"Error in OpenAI chat completion: {e}")
            raise
    
    def transcribe_audio(self, 
                        audio_bytes: bytes,
                        language: Optional[str] = None) -> Dict[str, Any]:
        """Transcribe audio using Whisper"""
        if not self._initialized:
            raise RuntimeError("OpenAI provider not initialized")
        
        try:
            import io
            audio_buffer = io.BytesIO(audio_bytes)
            audio_buffer.name = "audio.wav"
            
            response = self.client.audio.transcriptions.create(
                model=self.transcribe_model,
                file=audio_buffer,
                language=language
            )
            
            return {
                'text': response.text,
                'model': self.transcribe_model
            }
        except Exception as e:
            print(f"Error in OpenAI transcription: {e}")
            raise
    
    def vision_analysis(self, 
                       image_base64: str, 
                       prompt: str,
                       model: Optional[str] = None) -> Dict[str, Any]:
        """Analyze image using OpenAI Vision API"""
        if not self._initialized:
            raise RuntimeError("OpenAI provider not initialized")
        
        model = model or self.vision_model
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            
            return {
                'content': response.choices[0].message.content,
                'model': model
            }
        except Exception as e:
            print(f"Error in OpenAI vision analysis: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if OpenAI provider is available"""
        return self._initialized
    
    def get_provider_info(self) -> Dict[str, str]:
        """Get provider information"""
        return {
            'provider_name': 'OpenAI',
            'chat_model': self.chat_model,
            'vision_model': self.vision_model,
            'transcribe_model': self.transcribe_model
        }

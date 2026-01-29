"""Google Gemini implementation of LLMProvider"""

import os
from typing import Dict, List, Any, Optional
from .llm_interface import LLMProvider

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False


class GeminiProvider(LLMProvider):
    """Google Gemini provider supporting multiple models"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Gemini provider
        
        Args:
            config: Configuration dictionary containing:
                - GEMINI_API_KEY: API key
                - GEMINI_MODEL: Default chat model (default: gemini-2.0-flash)
                - GEMINI_VISION_MODEL: Vision model (default: gemini-2.0-flash)
        """
        if not HAS_GEMINI:
            raise ImportError("Google Generative AI SDK not installed. Install with: pip install google-generativeai")
        
        self.api_key = config.get('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not provided in config")
        
        genai.configure(api_key=self.api_key)
        
        self.chat_model = config.get('GEMINI_MODEL', 'gemini-2.0-flash')
        self.vision_model = config.get('GEMINI_VISION_MODEL', 'gemini-2.0-flash')
        
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize Gemini provider"""
        try:
            # Test by listing models
            genai.list_models()
            self._initialized = True
            print(f"✓ Gemini initialized (chat: {self.chat_model}, vision: {self.vision_model})")
            return True
        except Exception as e:
            print(f"⚠ Gemini initialization failed: {e}")
            self._initialized = False
            return False
    
    def chat_completion(self, 
                       messages: List[Dict[str, str]], 
                       model: Optional[str] = None,
                       temperature: float = 0.7,
                       max_tokens: int = 1024,
                       **kwargs) -> Dict[str, Any]:
        """Get chat completion from Gemini"""
        if not self._initialized:
            raise RuntimeError("Gemini provider not initialized")
        
        model = model or self.chat_model
        
        try:
            # Create model and prepare messages
            gemini_model = genai.GenerativeModel(model)
            
            # Convert messages to Gemini format
            gemini_messages = []
            for msg in messages:
                role = "user" if msg.get("role") == "user" else "model"
                gemini_messages.append({"role": role, "parts": [msg.get("content", "")]})
            
            # Generate response
            response = gemini_model.generate_content(
                gemini_messages,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                    **kwargs
                }
            )
            
            return {
                'content': response.text,
                'model': model
            }
        except Exception as e:
            print(f"Error in Gemini chat completion: {e}")
            raise
    
    def transcribe_audio(self, 
                        audio_bytes: bytes,
                        language: Optional[str] = None) -> Dict[str, Any]:
        """
        Gemini does not have native audio transcription.
        Use OpenAI Whisper as fallback or raise NotImplementedError
        """
        raise NotImplementedError("Gemini does not support audio transcription. Use OpenAI provider for Whisper.")
    
    def vision_analysis(self, 
                       image_base64: str, 
                       prompt: str,
                       model: Optional[str] = None) -> Dict[str, Any]:
        """Analyze image using Gemini Vision"""
        if not self._initialized:
            raise RuntimeError("Gemini provider not initialized")
        
        model = model or self.vision_model
        
        try:
            import base64
            from PIL import Image
            import io
            
            # Decode base64 image
            image_data = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_data))
            
            # Create model
            gemini_model = genai.GenerativeModel(model)
            
            # Generate response with image and prompt
            response = gemini_model.generate_content([prompt, image])
            
            return {
                'content': response.text,
                'model': model
            }
        except Exception as e:
            print(f"Error in Gemini vision analysis: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if Gemini provider is available"""
        return self._initialized
    
    def get_provider_info(self) -> Dict[str, str]:
        """Get provider information"""
        return {
            'provider_name': 'Google Gemini',
            'chat_model': self.chat_model,
            'vision_model': self.vision_model
        }

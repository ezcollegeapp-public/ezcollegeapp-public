"""AWS Bedrock implementation of LLMProvider"""

import os
import json
from typing import Dict, List, Any, Optional
from .llm_interface import LLMProvider

try:
    import boto3
    HAS_BEDROCK = True
except ImportError:
    HAS_BEDROCK = False


class BedrockProvider(LLMProvider):
    """AWS Bedrock provider supporting Claude and other models"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Bedrock provider
        
        Args:
            config: Configuration dictionary containing:
                - AWS_REGION: AWS region (default: us-east-2)
                - AWS_ACCESS_KEY_ID: AWS access key
                - AWS_SECRET_ACCESS_KEY: AWS secret key
                - BEDROCK_MODEL: Default model (default: claude-3-5-sonnet-20241022)
                - BEDROCK_VISION_MODEL: Vision model (default: claude-3-5-sonnet-20241022)
        """
        if not HAS_BEDROCK:
            raise ImportError("boto3 not installed. Install with: pip install boto3")
        
        region = config.get('AWS_REGION', 'us-east-2')
        access_key = config.get('AWS_ACCESS_KEY_ID')
        secret_key = config.get('AWS_SECRET_ACCESS_KEY')
        
        # Create Bedrock client
        self.client = boto3.client(
            'bedrock-runtime',
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        
        self.chat_model = config.get('BEDROCK_MODEL', 'claude-3-5-sonnet-20241022')
        self.vision_model = config.get('BEDROCK_VISION_MODEL', 'claude-3-5-sonnet-20241022')
        
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize Bedrock provider"""
        try:
            # Test connection by listing models
            self.client.list_foundation_models()
            self._initialized = True
            print(f"✓ Bedrock initialized (chat: {self.chat_model}, vision: {self.vision_model})")
            return True
        except Exception as e:
            print(f"⚠ Bedrock initialization failed: {e}")
            self._initialized = False
            return False
    
    def _extract_model_id(self, model: str) -> str:
        """Extract model ID from various formats"""
        # Handle different model reference formats
        if ':' in model:
            return model.split(':')[-1]
        return model
    
    def chat_completion(self, 
                       messages: List[Dict[str, str]], 
                       model: Optional[str] = None,
                       temperature: float = 0.7,
                       max_tokens: int = 1024,
                       **kwargs) -> Dict[str, Any]:
        """Get chat completion from Bedrock (Claude)"""
        if not self._initialized:
            raise RuntimeError("Bedrock provider not initialized")
        
        model = model or self.chat_model
        model_id = self._extract_model_id(model)
        
        try:
            # Prepare request
            request_body = {
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                **kwargs
            }
            
            # Call Bedrock
            response = self.client.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            content = response_body.get('content', [{}])[0].get('text', '')
            
            return {
                'content': content,
                'model': model
            }
        except Exception as e:
            print(f"Error in Bedrock chat completion: {e}")
            raise
    
    def transcribe_audio(self, 
                        audio_bytes: bytes,
                        language: Optional[str] = None) -> Dict[str, Any]:
        """
        Bedrock does not have native audio transcription.
        Use OpenAI Whisper as fallback or raise NotImplementedError
        """
        raise NotImplementedError("Bedrock does not support audio transcription. Use OpenAI provider for Whisper.")
    
    def vision_analysis(self, 
                       image_base64: str, 
                       prompt: str,
                       model: Optional[str] = None) -> Dict[str, Any]:
        """Analyze image using Bedrock Vision (Claude with vision)"""
        if not self._initialized:
            raise RuntimeError("Bedrock provider not initialized")
        
        model = model or self.vision_model
        model_id = self._extract_model_id(model)
        
        try:
            # Prepare message with image
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
            
            # Prepare request
            request_body = {
                "messages": messages,
                "max_tokens": 1024
            }
            
            # Call Bedrock
            response = self.client.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            content = response_body.get('content', [{}])[0].get('text', '')
            
            return {
                'content': content,
                'model': model
            }
        except Exception as e:
            print(f"Error in Bedrock vision analysis: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if Bedrock provider is available"""
        return self._initialized
    
    def get_provider_info(self) -> Dict[str, str]:
        """Get provider information"""
        return {
            'provider_name': 'AWS Bedrock',
            'chat_model': self.chat_model,
            'vision_model': self.vision_model
        }

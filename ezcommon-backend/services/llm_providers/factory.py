"""Factory for creating LLM provider instances"""

import os
from typing import Dict, Any
from .llm_interface import LLMProvider


class LLMProviderFactory:
    """Factory for creating LLM provider instances based on configuration"""
    
    @staticmethod
    def create(config: Dict[str, Any]) -> LLMProvider:
        """
        Create an LLM provider instance based on configuration
        
        Args:
            config: Configuration dictionary with:
                - LLM_PROVIDER: 'openai', 'gemini', or 'bedrock'
                - Provider-specific settings (API keys, models, etc.)
                
        Returns:
            LLMProvider instance
            
        Raises:
            ValueError: If provider type is not supported
        """
        provider_type = config.get('LLM_PROVIDER', 'openai').lower()
        
        if provider_type == 'openai':
            from .openai_provider import OpenAIProvider
            provider = OpenAIProvider(config)
        
        elif provider_type == 'gemini':
            from .gemini_provider import GeminiProvider
            provider = GeminiProvider(config)
        
        elif provider_type == 'bedrock':
            from .bedrock_provider import BedrockProvider
            provider = BedrockProvider(config)
        
        else:
            raise ValueError(
                f"Unsupported LLM provider: {provider_type}. "
                f"Supported providers: openai, gemini, bedrock"
            )
        
        # Initialize the provider
        provider.initialize()
        return provider


def _build_llm_config(provider_type: str = 'openai') -> Dict[str, Any]:
    """Build config from environment variables for legacy callers"""
    return {
        'LLM_PROVIDER': provider_type,
        'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY'),
        'OPENAI_MODEL': os.environ.get('OPENAI_MODEL', 'gpt-4o-mini'),
        'OPENAI_VISION_MODEL': os.environ.get('OPENAI_VISION_MODEL', 'gpt-4o'),
        'OPENAI_TRANSCRIBE_MODEL': os.environ.get('OPENAI_TRANSCRIBE_MODEL', 'whisper-1'),
        'GEMINI_API_KEY': os.environ.get('GEMINI_API_KEY'),
        'GEMINI_MODEL': os.environ.get('GEMINI_MODEL', 'gemini-2.0-flash'),
        'GEMINI_VISION_MODEL': os.environ.get('GEMINI_VISION_MODEL', 'gemini-1.5-pro'),
        'AWS_REGION': os.environ.get('AWS_REGION', 'us-east-1'),
    }


class LLMFactory:
    """Compatibility shim for legacy imports expecting LLMFactory"""

    @staticmethod
    def create_provider(provider_type: str = 'openai') -> LLMProvider:
        config = _build_llm_config(provider_type)
        return LLMProviderFactory.create(config)

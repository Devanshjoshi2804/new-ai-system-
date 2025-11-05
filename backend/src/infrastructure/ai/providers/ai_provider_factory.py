"""
AI Provider Factory - Automatically selects the best available AI provider
Prioritizes Groq for speed, falls back to Gemini or Mistral
"""
import os
import logging
from typing import Optional, Union
from enum import Enum

from src.infrastructure.ai.providers.groq_provider import GroqProvider
from src.infrastructure.ai.providers.gemini_provider import GeminiProvider
from src.infrastructure.ai.providers.mistral_provider import MistralProvider

logger = logging.getLogger(__name__)


class AIProviderType(str, Enum):
    """Available AI provider types"""
    GROQ = "groq"
    GEMINI = "gemini"
    MISTRAL = "mistral"
    AUTO = "auto"  # Automatically select best available


class AIProviderFactory:
    """
    Factory for creating AI providers with automatic fallback
    
    Priority order (for reasoning/analysis tasks):
    1. Groq (fastest, no rate limits on paid tier)
    2. Gemini (good quality, but has rate limits)
    3. Mistral (good for OCR, but limited for general tasks)
    """
    
    @staticmethod
    def create_provider(
        provider_type: AIProviderType = AIProviderType.AUTO,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> Union[GroqProvider, GeminiProvider, MistralProvider]:
        """
        Create an AI provider instance
        
        Args:
            provider_type: Which provider to use (AUTO will select best available)
            api_key: Optional API key (will use env vars if not provided)
            model_name: Optional model name
            
        Returns:
            Initialized AI provider
            
        Raises:
            ValueError: If no providers are available
        """
        
        if provider_type == AIProviderType.GROQ:
            return AIProviderFactory._create_groq(api_key, model_name)
        
        elif provider_type == AIProviderType.GEMINI:
            return AIProviderFactory._create_gemini(api_key, model_name)
        
        elif provider_type == AIProviderType.MISTRAL:
            return AIProviderFactory._create_mistral(api_key)
        
        elif provider_type == AIProviderType.AUTO:
            return AIProviderFactory._create_auto(api_key, model_name)
        
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")
    
    @staticmethod
    def _create_groq(api_key: Optional[str] = None, model_name: Optional[str] = None) -> GroqProvider:
        """Create Groq provider"""
        try:
            key = api_key or os.getenv("GROQ_API_KEY")
            if not key:
                raise ValueError("GROQ_API_KEY not available")
            
            provider = GroqProvider(api_key=key, model_name=model_name)
            logger.info("[OK] Using Groq AI (ultra-fast inference, 750+ tokens/sec)")
            return provider
        
        except Exception as e:
            logger.warning(f"Failed to initialize Groq provider: {e}")
            raise
    
    @staticmethod
    def _create_gemini(api_key: Optional[str] = None, model_name: Optional[str] = None) -> GeminiProvider:
        """Create Gemini provider"""
        try:
            key = api_key or os.getenv("GOOGLE_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not key:
                raise ValueError("GOOGLE_GEMINI_API_KEY not available")
            
            provider = GeminiProvider(api_key=key, model_name=model_name)
            logger.info("[OK] Using Google Gemini AI")
            return provider
        
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini provider: {e}")
            raise
    
    @staticmethod
    def _create_mistral(api_key: Optional[str] = None) -> MistralProvider:
        """Create Mistral provider"""
        try:
            key = api_key or os.getenv("MISTRAL_API_KEY")
            if not key:
                raise ValueError("MISTRAL_API_KEY not available")
            
            provider = MistralProvider(api_key=key)
            logger.info("[OK] Using Mistral AI")
            return provider
        
        except Exception as e:
            logger.warning(f"Failed to initialize Mistral provider: {e}")
            raise
    
    @staticmethod
    def _create_auto(api_key: Optional[str] = None, model_name: Optional[str] = None) -> Union[GroqProvider, GeminiProvider, MistralProvider]:
        """
        Automatically select best available provider
        
        Priority:
        1. Groq (fastest, best for production)
        2. Gemini (good quality, but rate limits)
        3. Mistral (fallback)
        """
        
        # Try Groq first (best option)
        try:
            provider = AIProviderFactory._create_groq(api_key, model_name)
            logger.info("[START] Auto-selected Groq (fastest inference)")
            return provider
        except Exception as e:
            logger.debug(f"Groq not available: {e}")
        
        # Try Gemini second
        try:
            provider = AIProviderFactory._create_gemini(api_key, model_name)
            logger.info("[INFO] Auto-selected Gemini (Groq not available)")
            return provider
        except Exception as e:
            logger.debug(f"Gemini not available: {e}")
        
        # Try Mistral as last resort
        try:
            provider = AIProviderFactory._create_mistral(api_key)
            logger.info("[NOTE] Auto-selected Mistral (Groq and Gemini not available)")
            return provider
        except Exception as e:
            logger.debug(f"Mistral not available: {e}")
        
        # No providers available
        raise ValueError(
            "No AI providers available! Please set one of: "
            "GROQ_API_KEY, GOOGLE_GEMINI_API_KEY, or MISTRAL_API_KEY"
        )
    
    @staticmethod
    def get_available_providers() -> list[str]:
        """Get list of available providers based on environment variables"""
        available = []
        
        if os.getenv("GROQ_API_KEY"):
            available.append("groq")
        
        if os.getenv("GOOGLE_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY"):
            available.append("gemini")
        
        if os.getenv("MISTRAL_API_KEY"):
            available.append("mistral")
        
        return available
    
    @staticmethod
    def get_recommended_provider() -> str:
        """Get the recommended provider based on what's available"""
        available = AIProviderFactory.get_available_providers()
        
        if "groq" in available:
            return "groq (recommended: fastest, no rate limits)"
        elif "gemini" in available:
            return "gemini (warning: has rate limits)"
        elif "mistral" in available:
            return "mistral (limited capabilities)"
        else:
            return "none (please configure an API key)"


# Convenience function for easy usage
def get_ai_provider(
    provider_type: AIProviderType = AIProviderType.AUTO,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None
) -> Union[GroqProvider, GeminiProvider, MistralProvider]:
    """
    Convenience function to get an AI provider
    
    Usage:
        # Auto-select best provider
        provider = get_ai_provider()
        
        # Force specific provider
        provider = get_ai_provider(AIProviderType.GROQ)
        
        # With custom API key
        provider = get_ai_provider(api_key="your-key")
    """
    return AIProviderFactory.create_provider(provider_type, api_key, model_name)



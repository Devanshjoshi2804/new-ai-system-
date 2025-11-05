"""
Groq AI Provider for fast inference with rate limit handling
"""
import os
import json
import logging
from typing import Optional, Dict, Any
import asyncio

logger = logging.getLogger(__name__)


class GroqProvider:
    """Groq AI provider for fast inference"""
    
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        """
        Initialize Groq provider
        
        Args:
            api_key: Groq API key (defaults to GROQ_API_KEY env var)
            model_name: Model to use (defaults to llama-3.3-70b-versatile)
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model_name = model_name or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        
        if not self.api_key:
            logger.warning("[WARN] GROQ_API_KEY not set - Groq provider will not be available")
            self.client = None
            return
        
        try:
            from groq import AsyncGroq
            self.client = AsyncGroq(api_key=self.api_key)
            logger.info(f"[OK] Groq provider initialized with model: {self.model_name}")
        except ImportError:
            logger.warning("[WARN] Groq library not installed - run: pip install groq")
            self.client = None
    
    async def generate_content(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate content using Groq
        
        Args:
            prompt: The prompt text
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            system_prompt: Optional system prompt
            
        Returns:
            Generated text
        """
        try:
            if not self.client:
                raise ValueError("Groq client not initialized")
            
            messages = []
            
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            # Call Groq API
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens or 8192
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"[ERROR] Groq generation error: {e}")
            raise
    
    async def generate_with_retry(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_retries: int = 3,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate content with automatic retry on rate limits
        
        Args:
            prompt: The prompt text
            temperature: Sampling temperature
            max_retries: Maximum retry attempts
            system_prompt: Optional system prompt
            
        Returns:
            Generated text
        """
        for attempt in range(max_retries):
            try:
                return await self.generate_content(
                    prompt=prompt,
                    temperature=temperature,
                    system_prompt=system_prompt
                )
            except Exception as e:
                if "rate_limit" in str(e).lower() and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # Exponential backoff
                    logger.warning(f"[WARN] Rate limit hit, waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    raise
        
        raise Exception("Max retries exceeded")


class MultiProviderAI:
    """
    Multi-provider AI with automatic fallback
    Tries Groq first (fast), falls back to Gemini if rate limited
    """
    
    def __init__(self):
        """Initialize multi-provider AI"""
        self.groq = None
        self.gemini = None
        
        # Try to initialize Groq
        try:
            self.groq = GroqProvider()
            if self.groq.client:
                logger.info("[OK] Groq provider available (primary)")
        except Exception as e:
            logger.warning(f"[WARN] Groq initialization failed: {e}")
        
        # Always initialize Gemini as fallback
        try:
            from src.infrastructure.ai.providers.gemini_provider import GeminiProvider
            self.gemini = GeminiProvider()
            logger.info("[OK] Gemini provider available (fallback)")
        except Exception as e:
            logger.error(f"[ERROR] Gemini initialization failed: {e}")
    
    async def generate_content(
        self,
        prompt: str,
        temperature: float = 0.7,
        prefer_speed: bool = True,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate content with automatic provider selection
        
        Args:
            prompt: The prompt text
            temperature: Sampling temperature
            prefer_speed: If True, try Groq first (faster)
            system_prompt: Optional system prompt
            
        Returns:
            Generated text
        """
        # Try Groq first if available and speed preferred
        if prefer_speed and self.groq and self.groq.client:
            try:
                logger.info("[START] Using Groq (fast)")
                return await self.groq.generate_content(
                    prompt=prompt,
                    temperature=temperature,
                    system_prompt=system_prompt
                )
            except Exception as e:
                logger.warning(f"[WARN] Groq failed: {e}, falling back to Gemini")
        
        # Fallback to Gemini
        if self.gemini:
            try:
                logger.info("[INFO] Using Gemini (fallback)")
                return await self.gemini.generate_content(
                    prompt=prompt,
                    temperature=temperature
                )
            except Exception as e:
                logger.error(f"[ERROR] Gemini also failed: {e}")
                raise
        
        raise Exception("No AI providers available")
    
    def get_available_providers(self) -> list[str]:
        """Get list of available providers"""
        providers = []
        if self.groq and self.groq.client:
            providers.append("groq")
        if self.gemini:
            providers.append("gemini")
        return providers


"""
AI API Integration Adapters

Provides consistent interface for HybridPredictor to call AI APIs (Groq, Gemini, Mistral).
Handles API calls, retry logic, and result formatting.
"""

import logging
from typing import Dict, Any, Optional
import asyncio
import os

logger = logging.getLogger(__name__)


class GroqProvider:
    """
    Groq AI provider (ultra-fast inference)

    Uses Groq's API for extremely fast LLM inference (<1s typically).
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Groq provider

        Args:
            api_key: Groq API key (defaults to env var)
        """
        self.api_key = api_key or os.getenv('GROQ_API_KEY')
        self.model = "mixtral-8x7b-32768"  # Fast and capable model
        self.client = None

        logger.info("[AI_ADAPTER] Groq provider initialized")

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        """
        Generate response using Groq

        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response
        """
        try:
            # Lazy import to avoid dependency issues
            from groq import AsyncGroq

            if not self.client:
                self.client = AsyncGroq(api_key=self.api_key)

            # Call Groq API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an API integration expert. Provide accurate, JSON-formatted responses."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )

            result = response.choices[0].message.content
            logger.debug(f"[AI_ADAPTER] Groq generated {len(result)} chars")

            return result

        except Exception as e:
            logger.error(f"[AI_ADAPTER] Groq error: {e}")
            raise


class GeminiProvider:
    """
    Google Gemini AI provider

    Uses Gemini Pro for high-quality responses.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini provider

        Args:
            api_key: Gemini API key (defaults to env var)
        """
        self.api_key = api_key or os.getenv('GOOGLE_GEMINI_API_KEY')
        self.model_name = "gemini-pro"
        self.model = None

        logger.info("[AI_ADAPTER] Gemini provider initialized")

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        """
        Generate response using Gemini

        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response
        """
        try:
            # Lazy import
            import google.generativeai as genai

            if not self.model:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(self.model_name)

            # Call Gemini API in thread pool (it's not async)
            def _generate():
                generation_config = {
                    'temperature': temperature,
                    'max_output_tokens': max_tokens
                }

                response = self.model.generate_content(
                    prompt,
                    generation_config=generation_config
                )

                return response.text

            result = await asyncio.to_thread(_generate)
            logger.debug(f"[AI_ADAPTER] Gemini generated {len(result)} chars")

            return result

        except Exception as e:
            logger.error(f"[AI_ADAPTER] Gemini error: {e}")
            raise


class MistralProvider:
    """
    Mistral AI provider

    Uses Mistral models for high-quality responses.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Mistral provider

        Args:
            api_key: Mistral API key (defaults to env var)
        """
        self.api_key = api_key or os.getenv('MISTRAL_API_KEY')
        self.model = "mistral-medium"
        self.client = None

        logger.info("[AI_ADAPTER] Mistral provider initialized")

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        """
        Generate response using Mistral

        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response
        """
        try:
            # Lazy import
            from mistralai.async_client import MistralAsyncClient
            from mistralai.models.chat_completion import ChatMessage

            if not self.client:
                self.client = MistralAsyncClient(api_key=self.api_key)

            # Call Mistral API
            messages = [
                ChatMessage(
                    role="system",
                    content="You are an API integration expert. Provide accurate, JSON-formatted responses."
                ),
                ChatMessage(
                    role="user",
                    content=prompt
                )
            ]

            response = await self.client.chat(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            result = response.choices[0].message.content
            logger.debug(f"[AI_ADAPTER] Mistral generated {len(result)} chars")

            return result

        except Exception as e:
            logger.error(f"[AI_ADAPTER] Mistral error: {e}")
            raise


class FallbackProvider:
    """
    Fallback provider that tries multiple AI APIs in sequence

    Tries providers in order until one succeeds.
    Order: Groq (fastest) → Gemini (reliable) → Mistral (fallback)
    """

    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        mistral_api_key: Optional[str] = None
    ):
        """
        Initialize fallback provider with multiple AI APIs

        Args:
            groq_api_key: Groq API key
            gemini_api_key: Gemini API key
            mistral_api_key: Mistral API key
        """
        self.providers = []

        # Add providers that have API keys
        if groq_api_key or os.getenv('GROQ_API_KEY'):
            self.providers.append(('groq', GroqProvider(groq_api_key)))
            logger.info("[AI_ADAPTER] Added Groq provider")

        if gemini_api_key or os.getenv('GOOGLE_GEMINI_API_KEY'):
            self.providers.append(('gemini', GeminiProvider(gemini_api_key)))
            logger.info("[AI_ADAPTER] Added Gemini provider")

        if mistral_api_key or os.getenv('MISTRAL_API_KEY'):
            self.providers.append(('mistral', MistralProvider(mistral_api_key)))
            logger.info("[AI_ADAPTER] Added Mistral provider")

        if not self.providers:
            logger.warning("[AI_ADAPTER] No AI providers configured!")

        logger.info(f"[AI_ADAPTER] FallbackProvider initialized with {len(self.providers)} providers")

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        """
        Generate response with automatic fallback

        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response

        Raises:
            Exception: If all providers fail
        """
        last_error = None

        for provider_name, provider in self.providers:
            try:
                logger.debug(f"[AI_ADAPTER] Trying {provider_name}...")

                result = await provider.generate(
                    prompt,
                    temperature=temperature,
                    max_tokens=max_tokens
                )

                logger.info(f"[AI_ADAPTER] {provider_name} succeeded")
                return result

            except Exception as e:
                logger.warning(f"[AI_ADAPTER] {provider_name} failed: {e}")
                last_error = e
                continue

        # All providers failed
        error_msg = f"All AI providers failed. Last error: {last_error}"
        logger.error(f"[AI_ADAPTER] {error_msg}")
        raise Exception(error_msg)


def create_ai_providers(
    default_provider: str = "groq",
    groq_api_key: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
    mistral_api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Factory function to create AI provider instances

    Args:
        default_provider: Default provider to use ('groq', 'gemini', 'mistral', or 'fallback')
        groq_api_key: Groq API key
        gemini_api_key: Gemini API key
        mistral_api_key: Mistral API key

    Returns:
        Dictionary mapping provider names to instances
    """
    providers = {}

    # Create individual providers if API keys are available
    if groq_api_key or os.getenv('GROQ_API_KEY'):
        providers['groq'] = GroqProvider(groq_api_key)

    if gemini_api_key or os.getenv('GOOGLE_GEMINI_API_KEY'):
        providers['gemini'] = GeminiProvider(gemini_api_key)

    if mistral_api_key or os.getenv('MISTRAL_API_KEY'):
        providers['mistral'] = MistralProvider(mistral_api_key)

    # Always create fallback provider
    providers['fallback'] = FallbackProvider(
        groq_api_key=groq_api_key,
        gemini_api_key=gemini_api_key,
        mistral_api_key=mistral_api_key
    )

    # Set default provider
    if default_provider in providers:
        providers['default'] = providers[default_provider]
    elif providers:
        # Use first available provider as default
        providers['default'] = list(providers.values())[0]

    logger.info(f"[AI_ADAPTER] Created {len(providers)} AI providers (default: {default_provider})")

    return providers

"""
AI Provider Fallback System
Automatically switches between Groq, Gemini, and Mistral when rate limits hit
"""
import os
import json
from typing import Tuple, Optional
from enum import Enum


class AIProvider(Enum):
    GROQ = "groq"
    GEMINI = "gemini"
    MISTRAL = "mistral"


class AIProviderFallback:
    """
    Smart AI provider with automatic fallback
    Priority: Groq (fastest) → Gemini (free tier) → Mistral (backup)
    """
    
    def __init__(self):
        self.providers = [AIProvider.GROQ, AIProvider.GEMINI, AIProvider.MISTRAL]
        self.current_provider_index = 0
        
        # Initialize all clients
        self._init_groq()
        self._init_gemini()
        self._init_mistral()
    
    def _init_groq(self):
        """Initialize Groq client"""
        try:
            from langchain_groq import ChatGroq
            self.groq_client = ChatGroq(
                model="meta-llama/llama-4-maverick-17b-128e-instruct",
                temperature=0,
                max_tokens=None,
                timeout=None,
                max_retries=1,  # Don't retry, just fallback
            )
            print("[OK] Groq initialized")
        except Exception as e:
            print(f"[WARN] Groq initialization failed: {e}")
            self.groq_client = None
    
    def _init_gemini(self):
        """Initialize Gemini client"""
        try:
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GOOGLE_GEMINI_API_KEY"))
            self.gemini_client = genai.GenerativeModel('gemini-1.5-flash')
            print("[OK] Gemini initialized")
        except Exception as e:
            print(f"[WARN] Gemini initialization failed: {e}")
            self.gemini_client = None
    
    def _init_mistral(self):
        """Initialize Mistral client"""
        try:
            from mistralai import Mistral
            self.mistral_client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
            print("[OK] Mistral initialized")
        except Exception as e:
            print(f"[WARN] Mistral initialization failed: {e}")
            self.mistral_client = None
    
    def generate(self, prompt: str, system_prompt: str = "You are a helpful AI assistant.") -> Tuple[Optional[str], AIProvider]:
        """
        Generate response with automatic fallback
        Returns: (response_text, provider_used)
        """
        for attempt in range(len(self.providers)):
            provider = self.providers[self.current_provider_index]
            
            try:
                if provider == AIProvider.GROQ and self.groq_client:
                    print(f"[AI] Trying Groq (attempt {attempt + 1})...")
                    response = self._generate_groq(prompt, system_prompt)
                    print(f"[OK] Groq succeeded!")
                    return response, AIProvider.GROQ
                
                elif provider == AIProvider.GEMINI and self.gemini_client:
                    print(f"[AI] Trying Gemini (attempt {attempt + 1})...")
                    response = self._generate_gemini(prompt, system_prompt)
                    print(f"[OK] Gemini succeeded!")
                    return response, AIProvider.GEMINI
                
                elif provider == AIProvider.MISTRAL and self.mistral_client:
                    print(f"[AI] Trying Mistral (attempt {attempt + 1})...")
                    response = self._generate_mistral(prompt, system_prompt)
                    print(f"[OK] Mistral succeeded!")
                    return response, AIProvider.MISTRAL
            
            except Exception as e:
                error_msg = str(e).lower()
                
                # Check if it's a rate limit error
                if any(x in error_msg for x in ['429', 'rate limit', 'too many requests', 'capacity exceeded']):
                    print(f"[WARN] {provider.value.upper()} hit rate limit, switching to next provider...")
                    self._switch_provider()
                else:
                    print(f"[ERROR] {provider.value.upper()} error: {e}")
                    self._switch_provider()
        
        # All providers failed
        print("[ERROR] ALL AI PROVIDERS FAILED!")
        return None, None
    
    def _generate_groq(self, prompt: str, system_prompt: str) -> str:
        """Generate using Groq"""
        messages = [
            ("system", system_prompt),
            ("human", prompt)
        ]
        response = self.groq_client.invoke(messages)
        return response.content.strip()
    
    def _generate_gemini(self, prompt: str, system_prompt: str) -> str:
        """Generate using Gemini"""
        full_prompt = f"{system_prompt}\n\n{prompt}"
        response = self.gemini_client.generate_content(full_prompt)
        return response.text.strip()
    
    def _generate_mistral(self, prompt: str, system_prompt: str) -> str:
        """Generate using Mistral"""
        from mistralai import UserMessage, SystemMessage
        
        messages = [
            SystemMessage(content=system_prompt),
            UserMessage(content=prompt)
        ]
        
        response = self.mistral_client.chat.complete(
            model="mistral-large-latest",
            messages=messages
        )
        
        return response.choices[0].message.content.strip()
    
    def _switch_provider(self):
        """Switch to next provider in rotation"""
        self.current_provider_index = (self.current_provider_index + 1) % len(self.providers)
        print(f"[SWITCH] Now using {self.providers[self.current_provider_index].value.upper()}")
    
    def reset_to_primary(self):
        """Reset to primary provider (Groq)"""
        self.current_provider_index = 0
        print("[RESET] Back to primary provider (Groq)")


# Global instance
_ai_fallback = None

def get_ai_provider() -> AIProviderFallback:
    """Get or create global AI provider instance"""
    global _ai_fallback
    if _ai_fallback is None:
        _ai_fallback = AIProviderFallback()
    return _ai_fallback



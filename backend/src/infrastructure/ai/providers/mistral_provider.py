"""
Mistral AI provider with OCR capabilities
"""
import logging
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
from mistralai import Mistral

from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class MistralProvider:
    """Mistral AI provider with OCR support"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Mistral provider"""
        self.api_key = api_key or settings.mistral_api_key
        if not self.api_key:
            logger.warning("Mistral API key not configured - OCR features will not be available")
            self.client = None
            self.ocr_model = None
            return
        
        self.client = Mistral(api_key=self.api_key)
        self.ocr_model = "pixtral-12b-2409"  # Vision model for OCR
    
    async def process_document(
        self,
        document_path: Optional[str] = None,
        document_url: Optional[str] = None,
        document_bytes: Optional[bytes] = None,
        include_images: bool = True,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process document using Mistral OCR with base64 encoding
        
        Args:
            document_path: Local path to document
            document_url: URL to document
            document_bytes: Document as bytes
            include_images: Whether to include extracted images
            prompt: Optional prompt for document understanding
            
        Returns:
            OCR results with extracted text and images
        """
        try:
            import base64
            import asyncio
            
            # Check if client is available
            if not self.client:
                raise ValueError("Mistral API key not configured")
            
            # Prepare document as base64
            if document_url:
                # Use URL directly
                document_content = {
                    "type": "document_url",
                    "document_url": document_url
                }
            elif document_path:
                # Read file and encode to base64
                def read_file():
                    with open(document_path, "rb") as f:
                        return base64.b64encode(f.read()).decode('utf-8')
                
                base64_data = await asyncio.to_thread(read_file)
                document_content = {
                    "type": "image_url",
                    "image_url": f"data:application/pdf;base64,{base64_data}"
                }
            elif document_bytes:
                # Encode bytes to base64
                base64_data = base64.b64encode(document_bytes).decode('utf-8')
                document_content = {
                    "type": "image_url",
                    "image_url": f"data:application/pdf;base64,{base64_data}"
                }
            else:
                raise ValueError("Must provide document_path, document_url, or document_bytes")
            
            # Process with OCR using chat completion
            messages = []
            
            if prompt:
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        document_content
                    ]
                })
            else:
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract all text and data from this document."},
                        document_content
                    ]
                })
            
            # Make the API call in a thread to avoid blocking
            def make_request():
                return self.client.chat.complete(
                    model=self.ocr_model,
                    messages=messages
                )
            
            response = await asyncio.to_thread(make_request)
            
            # Extract results
            result = {
                "text": response.choices[0].message.content,
                "images": [],
                "metadata": {
                    "model": self.ocr_model,
                    "usage": response.usage.model_dump() if hasattr(response, 'usage') else None
                }
            }
            
            # Extract images if available
            if include_images and hasattr(response.choices[0].message, 'content_items'):
                for item in response.choices[0].message.content_items:
                    if item.type == "image":
                        result["images"].append({
                            "data": item.data,
                            "mime_type": item.mime_type
                        })
            
            return result
        
        except Exception as e:
            logger.error(f"Mistral OCR error: {e}", exc_info=True)
            raise
    
    async def extract_structured_data(
        self,
        document_path: Optional[str] = None,
        document_url: Optional[str] = None,
        document_bytes: Optional[bytes] = None,
        extraction_prompt: str = "",
        output_schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract structured data from document (doc-as-prompt)
        
        Args:
            document_path: Local path to document
            document_url: URL to document
            document_bytes: Document as bytes
            extraction_prompt: Prompt describing what to extract
            output_schema: JSON schema for structured output
            
        Returns:
            Extracted structured data
        """
        try:
            # Build extraction prompt
            full_prompt = extraction_prompt
            
            if output_schema:
                import json
                full_prompt += f"\n\nOutput the extracted data as JSON matching this schema:\n{json.dumps(output_schema, indent=2)}"
            else:
                full_prompt += "\n\nOutput the extracted data as structured JSON."
            
            # Process document with prompt
            result = await self.process_document(
                document_path=document_path,
                document_url=document_url,
                document_bytes=document_bytes,
                include_images=False,
                prompt=full_prompt
            )
            
            # Parse JSON from response
            import json
            text = result["text"]
            
            # Extract JSON from response (may be wrapped in markdown)
            if "```json" in text:
                json_start = text.find("```json") + 7
                json_end = text.find("```", json_start)
                text = text[json_start:json_end].strip()
            elif "```" in text:
                json_start = text.find("```") + 3
                json_end = text.find("```", json_start)
                text = text[json_start:json_end].strip()
            
            extracted_data = json.loads(text)
            
            return {
                "data": extracted_data,
                "metadata": result["metadata"]
            }
        
        except Exception as e:
            logger.error(f"Mistral structured extraction error: {e}")
            raise
    
    async def generate_content(
        self,
        prompt: str,
        model: str = "mistral-large-latest",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate content using Mistral text models
        
        Args:
            prompt: The prompt text
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        try:
            import asyncio
            
            if not self.client:
                raise ValueError("Mistral API key not configured")
            
            messages = [{"role": "user", "content": prompt}]
            
            # Run in thread to avoid blocking
            def make_request():
                return self.client.chat.complete(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            
            response = await asyncio.to_thread(make_request)
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Mistral generation error: {e}", exc_info=True)
            raise



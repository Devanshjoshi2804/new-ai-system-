"""
PDF parser using PyMuPDF (via LangChain) and Groq AI
"""
import asyncio
import logging
from typing import Optional, List, Dict, Any
from fastapi import UploadFile
from pathlib import Path
import tempfile
import os
import json

from src.application.ai.parsers.base_parser import BaseParser
from src.domain.value_objects.doc_format import DocFormat
from src.domain.value_objects.api_schema import APISpecification, AuthConfig, AuthType
from src.domain.value_objects.api_endpoint import APIEndpoint, HTTPMethod, APIParameter, ParameterLocation
from src.infrastructure.ai.providers.groq_provider import GroqProvider
from src.infrastructure.ai.providers.gemini_provider import GeminiProvider
from src.infrastructure.ai.providers.mistral_provider import MistralProvider

logger = logging.getLogger(__name__)


class MultiAIProvider:
    """
    Multi-provider AI with automatic fallback on rate limits
    Priority: Groq (fastest) -> Gemini (free) -> Mistral (backup)
    """
    
    def __init__(self):
        self.providers = []
        self.provider_names = []
        
        # Try to initialize all providers
        try:
            groq = GroqProvider()
            if groq.client:
                self.providers.append(groq)
                self.provider_names.append("Groq")
                logger.info("[OK] Groq provider available (fastest)")
        except Exception as e:
            logger.warning(f"[WARN] Groq initialization failed: {e}")
        
        try:
            gemini = GeminiProvider()
            self.providers.append(gemini)
            self.provider_names.append("Gemini")
            logger.info("[OK] Gemini provider available (free & reliable)")
        except Exception as e:
            logger.warning(f"[WARN] Gemini initialization failed: {e}")
        
        try:
            mistral = MistralProvider()
            if mistral.client:
                self.providers.append(mistral)
                self.provider_names.append("Mistral")
                logger.info("[OK] Mistral provider available (backup)")
        except Exception as e:
            logger.warning(f"[WARN] Mistral initialization failed: {e}")
        
        if not self.providers:
            raise ValueError("No AI providers available - check API keys")
        
        logger.info(f"[AI] Multi-AI Provider initialized with {len(self.providers)} providers: {', '.join(self.provider_names)}")
    
    async def generate_content(self, prompt: str, temperature: float = 0.1, max_tokens: int = 8192) -> tuple[str, str]:
        """
        Generate content with automatic provider fallback
        
        Returns:
            Tuple of (generated_text, provider_name)
        """
        last_error = None
        
        for provider, provider_name in zip(self.providers, self.provider_names):
            try:
                logger.info(f"[INFO] Trying {provider_name}...")
                
                if provider_name == "Groq":
                    result = await provider.generate_content(
                        prompt=prompt,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                elif provider_name == "Gemini":
                    result = await provider.generate_content(
                        prompt=prompt,
                        temperature=temperature,
                        use_cache=False
                    )
                elif provider_name == "Mistral":
                    result = await provider.generate_content(
                        prompt=prompt,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                
                logger.info(f"[OK] Successfully used {provider_name}")
                return result, provider_name
                
            except Exception as e:
                error_str = str(e).lower()
                
                # Check if it's a rate limit error
                if "429" in error_str or "rate" in error_str or "limit" in error_str or "quota" in error_str:
                    logger.warning(f"[WARN] {provider_name} rate limited: {e}")
                    last_error = e
                    continue  # Try next provider
                else:
                    # For other errors, also try next provider
                    logger.error(f"[ERROR] {provider_name} error: {e}")
                    last_error = e
                    continue
        
        # All providers failed
        raise Exception(f"All AI providers failed. Last error: {last_error}")


class PDFParser(BaseParser):
    """
    Parse API documentation from PDFs using PyMuPDF and Multi-AI providers
    
    Features:
    - Fast PDF text extraction using PyMuPDF (via LangChain)
    - Page-by-page processing with metadata
    - Retry mechanisms for robust extraction
    - Multi-AI provider with automatic fallback (Groq -> Gemini -> Mistral)
    """
    
    def __init__(self):
        self.ai_provider = MultiAIProvider()
        logger.info("[FILE] PDF Parser initialized with Multi-AI Provider")
    
    @property
    def supported_formats(self) -> list[DocFormat]:
        return [DocFormat.PDF]
    
    async def can_parse(self, file: UploadFile) -> bool:
        """Check if file is PDF"""
        if file.content_type == "application/pdf":
            return True
        
        if file.filename and file.filename.lower().endswith('.pdf'):
            return True
        
        # Check magic bytes
        content = await file.read(4)
        await file.seek(0)
        return content.startswith(b'%PDF')
    
    async def detect_format(self, file: UploadFile) -> tuple[DocFormat, float]:
        """Detect PDF format"""
        if await self.can_parse(file):
            return DocFormat.PDF, 0.99
        return DocFormat.UNKNOWN, 0.0
    
    async def analyze_extracted_text(self, extracted_text_data: Dict[str, Any]) -> APISpecification:
        """
        Analyze already-extracted text with Mistral AI to extract API specification
        This is called separately after text extraction via the /analyze endpoint
        """
        try:
            document_text = extracted_text_data.get("full_text", "")
            pages_data = extracted_text_data.get("pages", [])
            page_count = extracted_text_data.get("page_count", 0)
            
            logger.info(f"[INFO] Analyzing extracted text ({len(document_text)} chars) with Mistral AI...")
            
            # Analyze with Mistral AI to extract API specification
            api_data = await self._extract_api_specification_from_text(document_text)
            
            # Convert to APISpecification object
            api_spec = self._convert_to_api_spec(api_data)
            
            # Add extracted text metadata to schemas
            if not api_spec.schemas:
                api_spec.schemas = {}
            
            api_spec.schemas["extracted_text"] = {
                "full_text": document_text,
                "pages": pages_data,
                "page_count": page_count,
                "total_characters": len(document_text),
                "extraction_method": "PyMuPDF4LLM",
                "ai_analysis_completed": True
            }
            
            logger.info(f"[OK] AI analysis complete: {len(api_spec.endpoints)} endpoints found")
            
            return api_spec
            
        except Exception as e:
            logger.error(f"[ERROR] Error analyzing text: {e}")
            raise ValueError(f"Failed to analyze text: {str(e)}")
    
    async def parse(self, file: UploadFile) -> APISpecification:
        """
        Parse PDF API documentation using PyMuPDF and Mistral AI
        """
        try:
            logger.info(f"[FILE] Parsing PDF: {file.filename}")
            
            # Read file content
            content = await file.read()
            await file.seek(0)
            
            # Create temp file with explicit close to avoid Windows locking issues
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            try:
                tmp_file.write(content)
                tmp_file.flush()  # Ensure all data is written
                tmp_path = tmp_file.name
            finally:
                tmp_file.close()  # Explicitly close before PyMuPDF opens it
            
            try:
                # Step 1: Extract text using PyMuPDF4LLM with retry mechanism
                logger.info("[INFO] Extracting text from PDF using PyMuPDF4LLM (optimized for LLMs)...")
                extracted_result = await self._extract_text_with_pymupdf(tmp_path, file.filename)
                
                document_text = extracted_result["full_text"]
                page_count = extracted_result["page_count"]
                pages_data = extracted_result["pages"]
                
                logger.info(f"[OK] Extracted {len(document_text)} characters from {page_count} pages")
                
                # Save extraction results for debugging
                tmp_path_obj = Path(tmp_path)
                extraction_cache_path = tmp_path_obj.parent / f"{tmp_path_obj.stem}_extraction_result.json"
                with open(extraction_cache_path, 'w', encoding='utf-8') as f:
                    json.dump(extracted_result, f, ensure_ascii=False, indent=2)
                logger.info(f"[FLOPPY] Extraction results saved to: {extraction_cache_path}")
                
                # Return just the extracted text WITHOUT AI analysis
                # AI analysis will be triggered separately via /analyze endpoint
                logger.info("[OK] Text extraction complete - AI analysis can be triggered separately")
                
                # Create a minimal API spec with only extracted text (no endpoints yet)
                api_spec = APISpecification(
                    title="API Documentation (Text Extracted)",
                    version="1.0.0",
                    description=f"Text extraction completed. {page_count} pages extracted. Click 'Analyze with AI' to extract endpoints.",
                    base_url="",
                    endpoints=[],  # No endpoints yet
                    auth=None,
                    schemas={
                        "extracted_text": {
                            "full_text": document_text,
                            "pages": pages_data,
                            "page_count": page_count,
                            "total_characters": len(document_text),
                            "extraction_method": "PyMuPDF4LLM",
                            "cache_file": str(extraction_cache_path),
                            "ai_analysis_pending": True  # Flag to show AI analysis not done yet
                        }
                    }
                )
                
                logger.info(f"[OK] Successfully extracted PDF text: {page_count} pages, {len(document_text)} characters")
                
                return api_spec
            
            finally:
                # Clean up temp file (with retry for Windows file locking)
                if os.path.exists(tmp_path):
                    max_cleanup_attempts = 3
                    for cleanup_attempt in range(max_cleanup_attempts):
                        try:
                            # Small delay to ensure file handles are released
                            await asyncio.sleep(0.1)
                            os.unlink(tmp_path)
                            logger.debug(f"[OK] Cleaned up temp file: {tmp_path}")
                            break
                        except PermissionError as e:
                            if cleanup_attempt < max_cleanup_attempts - 1:
                                logger.warning(f"[WARN] File locked, retrying cleanup (attempt {cleanup_attempt + 1}/{max_cleanup_attempts})")
                                await asyncio.sleep(0.5)
                            else:
                                logger.warning(f"[WARN] Could not delete temp file (will be cleaned by OS): {tmp_path}")
                        except Exception as e:
                            logger.warning(f"[WARN] Error cleaning up temp file: {e}")
        
        except Exception as e:
            logger.error(f"[ERROR] Error parsing PDF: {e}")
            raise ValueError(f"Failed to parse PDF: {str(e)}")
    
    async def _extract_text_with_pymupdf(
        self,
        pdf_path: str,
        filename: str,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Extract text from PDF using PyMuPDF4LLM (optimized for LLM processing) with retry mechanism
        """
        from langchain_pymupdf4llm import PyMuPDF4LLMLoader
        
        for attempt in range(max_retries):
            try:
                logger.info(f"[INFO] Loading PDF with PyMuPDF4LLM (attempt {attempt + 1}/{max_retries})...")
                
                # Run in thread to avoid blocking
                def load_pdf():
                    loader = PyMuPDF4LLMLoader(
                        pdf_path,
                        mode="page"  # Load page by page with metadata
                    )
                    return loader.load()
                
                # Add timeout of 60 seconds
                docs = await asyncio.wait_for(
                    asyncio.to_thread(load_pdf),
                    timeout=60.0
                )
                
                logger.info(f"[OK] Loaded {len(docs)} pages from PDF")
                
                # Extract text and metadata from all pages
                pages_data = []
                full_text = ""
                
                for idx, doc in enumerate(docs):
                    page_num = idx + 1
                    page_text = doc.page_content
                    page_metadata = doc.metadata
                    
                    pages_data.append({
                        "page_number": page_num,
                        "text": page_text,
                        "char_count": len(page_text),
                        "metadata": page_metadata
                    })
                    
                    # Add to full text with page separator
                    full_text += f"\n\n--- Page {page_num} ---\n\n{page_text}"
                
                logger.info(f"[OK] Extracted {len(full_text)} total characters")
                
                # Explicitly clear docs to release file handles
                result = {
                    "full_text": full_text.strip(),
                    "pages": pages_data,
                    "page_count": len(docs),
                    "filename": filename
                }
                
                # Clear references to help garbage collection
                del docs
                del pages_data
                
                # Force garbage collection to release file handles (important for Windows)
                import gc
                gc.collect()
                
                # Small delay to ensure file handles are fully released
                await asyncio.sleep(0.1)
                
                return result
                
            except asyncio.TimeoutError:
                logger.error(f"[ERROR] PDF extraction timed out (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    logger.warning(f"⏳ Retrying in 3s...")
                    await asyncio.sleep(3)
                    continue
                else:
                    raise Exception("PDF extraction timed out after multiple attempts")
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"[ERROR] Error extracting PDF (attempt {attempt + 1}/{max_retries}): {error_msg}")
                
                if attempt < max_retries - 1:
                    logger.warning(f"⏳ Retrying in 3s...")
                    await asyncio.sleep(3)
                    continue
                else:
                    raise Exception(f"Failed to extract PDF after {max_retries} attempts: {error_msg}")
    
    async def _extract_api_specification_from_text(
        self,
        document_text: str
    ) -> Dict[str, Any]:
        """
        Extract structured API data from extracted text using Mistral AI
        """
        logger.info("[INFO] Using Mistral AI to analyze and extract API specification...")
        
        extraction_prompt = """You are an expert API documentation analyzer. Extract EXACT field names and specifications from documentation tables and examples.

**CRITICAL INSTRUCTIONS - READ CAREFULLY:**

1. **FIND TABLES** in the documentation showing "Request Body" or "Parameters" or "Field Description"
2. **EXTRACT EXACT field names** from the left column (Variable Name / Field Name)
3. **CHECK "Required" column** - mark fields as required ONLY if marked "Yes" or "[OK]"
4. **READ example JSON** - use the EXACT field names and value formats shown
5. **DO NOT** invent, guess, or modify field names
6. **DO NOT** use generic examples like "string", "test", "123" - use actual examples from docs

**EXAMPLE - How to extract from a table:**

Documentation shows:
```
Variable Name    Type      Required   Description
email            string    [OK] Yes     User email
password         string    [OK] Yes     Password
vendorType       string    [OK] Yes     Type of vendor
```

Request Body Example:
```json
{
  "email": "bhaveshqa20@yopmail.com",
  "password": "Test@1234",
  "vendorType": "SELLER"
}
```

**YOUR EXTRACTION** should produce:
```json
{
  "method": "POST",
  "path": "/api/endpoint",
  "parameters": [
    {
      "name": "email",
      "location": "body",
      "type": "string",
      "required": true,
      "description": "User email",
      "example": "bhaveshqa20@yopmail.com"
    },
    {
      "name": "password",
      "location": "body",
      "type": "string",
      "required": true,
      "description": "Password",
      "example": "Test@1234"
    },
    {
      "name": "vendorType",
      "location": "body",
      "type": "string",
      "required": true,
      "description": "Type of vendor",
      "example": "SELLER"
    }
  ],
  "request_body_schema": {
    "type": "object",
    "properties": {
      "email": {"type": "string", "example": "bhaveshqa20@yopmail.com"},
      "password": {"type": "string", "example": "Test@1234"},
      "vendorType": {"type": "string", "example": "SELLER"}
    },
    "required": ["email", "password", "vendorType"]
  }
}
```

**LOOK FOR:**
1. **Base URL**: Full API endpoint URLs (https://api.example.com)
2. **API Endpoints**: Method + Path
   - Example: "POST /cargo-api/onboarding"
   - Example: "GET /api/v1/users/{userId}"
3. **Parameter Tables**: Tables with columns like:
   - "Variable Name" or "Field" or "Parameter Name"
   - "Type" or "Data Type"
   - "Required" ([OK] / [ERROR] / Yes / No)
   - "Description"
4. **Example JSON**: Request body examples in code blocks
   - Extract EXACT field names (preserve case!)
   - Extract EXACT example values
5. **Query Parameters**: For GET requests, look for URL parameters
6. **Response Structure**: Success and Error response examples

**OUTPUT FORMAT** - Valid JSON ONLY (no markdown, no explanations):
{
  "title": "API Name from docs",
  "version": "1.0.0",
  "description": "Brief description",
  "base_url": "https://api.example.com",
  "auth": {
    "type": "api_key" or "bearer" or "none",
    "header_name": "Authorization",
    "details": {}
  },
  "endpoints": [
    {
      "method": "POST",
      "path": "/api/resource",
      "summary": "Brief description from docs",
      "description": "Detailed description",
      "parameters": [
        {
          "name": "EXACT_field_name_from_table",
          "location": "body" or "query" or "path",
          "type": "string",
          "required": true,
          "description": "From docs",
          "example": "exact_value_from_example_json"
        }
      ],
      "request_body_schema": {
        "type": "object",
        "properties": {
          "field1": {"type": "string", "example": "value_from_docs"},
          "field2": {"type": "number", "example": 123}
        },
        "required": ["field1", "field2"]
      },
      "response_examples": {
        "200": {"status": 200, "data": {}},
        "400": {"status": 400, "error": "Error message"}
      },
      "auth_required": true
    }
  ],
  "schemas": {},
  "workflows": {}
}

**CRITICAL REMINDERS:**
- Use EXACT field names from tables (preserve case: "vendorCode" not "vendor_code")
- Use EXACT example values from JSON examples
- Mark required=true ONLY if explicitly marked as required
- Extract ALL fields from tables, don't skip any
- If you see nested objects in examples, preserve the structure

**API Documentation Text:**
"""
        
        # For large documents, use chunked analysis
        max_chunk_size = 12000
        
        if len(document_text) > max_chunk_size:
            logger.info(f"[FILE] Document is large ({len(document_text)} chars), using chunked analysis...")
            return await self._extract_api_specification_chunked(document_text, max_chunk_size)
        
        # For smaller documents, analyze in one go
        full_prompt = extraction_prompt + document_text[:max_chunk_size]
        
        # Call Multi-AI provider (will auto-fallback on rate limits)
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                logger.info(f"[INFO] Calling Multi-AI Provider (attempt {attempt + 1}/{max_retries})...")
                
                # Use Multi-AI Provider with automatic fallback
                result_text, provider_used = await self.ai_provider.generate_content(
                    prompt=full_prompt,
                    temperature=0.1,
                    max_tokens=8192
                )
                
                logger.info(f"[OK] Received response from {provider_used} ({len(result_text)} chars)")
                
                # Parse JSON (handle markdown wrapping)
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0].strip()
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0].strip()
                
                extracted_data = json.loads(result_text)
                logger.info(f"[OK] Parsed JSON successfully: {len(extracted_data.get('endpoints', []))} endpoints found")
                
                return extracted_data
                
            except asyncio.TimeoutError:
                logger.error(f"[ERROR] Groq AI call timed out after 120s (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    logger.warning(f"⏳ Retrying in 5s...")
                    await asyncio.sleep(5)
                    continue
                else:
                    raise Exception("Groq AI analysis timed out after multiple attempts")
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"[ERROR] Error calling Groq AI (attempt {attempt + 1}/{max_retries}): {error_msg}")
                
                # Check if it's a rate limit error
                is_rate_limit = (
                    "429" in error_msg or 
                    "rate" in error_msg.lower() or 
                    "capacity" in error_msg.lower() or
                    "exceeded" in error_msg.lower()
                )
                
                if is_rate_limit and attempt < max_retries - 1:
                    # Exponential backoff: 5s, 10s, 20s
                    wait_time = 5 * (2 ** attempt)
                    logger.warning(f"⏳ Rate limited, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                elif attempt < max_retries - 1:
                    logger.warning(f"⏳ Retrying in 3s...")
                    await asyncio.sleep(3)
                    continue
                else:
                    logger.error(f"[ERROR] All {max_retries} attempts failed")
                    return {
                        "title": "API Documentation",
          "version": "1.0.0",
                        "description": f"Error extracting API specification: {error_msg}",
          "base_url": "https://api.example.com",
                        "endpoints": [],
                        "error": error_msg
                    }
    
    async def _extract_api_specification_chunked(
        self,
        document_text: str,
        chunk_size: int = 12000
    ) -> Dict[str, Any]:
        """
        Extract API specification from large documents by processing in chunks
        """
        logger.info(f"[FILE] Starting chunked analysis with Groq: {len(document_text)} chars, chunk size: {chunk_size}")
        
        # Split document into chunks
        chunks = []
        for i in range(0, len(document_text), chunk_size):
            chunk = document_text[i:i + chunk_size]
            chunks.append(chunk)
        
        logger.info(f"[INFO] Split document into {len(chunks)} chunks")
        
        # Analyze each chunk
        all_endpoints = []
        base_url = None
        auth_info = None
        title = "API Documentation"
        description = "Extracted from documentation"
        
        for idx, chunk in enumerate(chunks):
            logger.info(f"[INFO] Analyzing chunk {idx + 1}/{len(chunks)} ({len(chunk)} chars)...")
            
            chunk_prompt = f"""You are analyzing part {idx + 1} of {len(chunks)} of an API documentation.
Extract API endpoints, base URLs, and authentication info from this section.

Output ONLY valid JSON (no markdown) in this structure:
{{
  "title": "API Name (if found)",
  "base_url": "https://api.example.com (if found)",
  "auth": {{"type": "api_key", "details": {{}}}} (if found),
          "endpoints": [
            {{
              "method": "POST",
      "path": "/api/v1/resource",
      "summary": "Brief description",
      "parameters": [],
      "request_body": {{}},
      "response": {{}}
    }}
  ]
}}

**Documentation Section:**
{chunk}
"""
            
            # Keep retrying this chunk until success (no skipping!)
            chunk_result = None
            chunk_attempt = 0
            
            while chunk_result is None:
                try:
                    chunk_attempt += 1
                    
                    # Use Multi-AI Provider with automatic fallback
                    result_text, provider_used = await self.ai_provider.generate_content(
                        prompt=chunk_prompt,
                        temperature=0.1,
                        max_tokens=8192
                    )
                    
                    # Parse JSON (handle markdown wrapping)
                    if "```json" in result_text:
                        result_text = result_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in result_text:
                        result_text = result_text.split("```")[1].split("```")[0].strip()
                    
                    chunk_result = json.loads(result_text)
                    logger.info(f"[OK] Successfully processed chunk {idx + 1} with {provider_used} (attempt {chunk_attempt})")
                    break  # Success!
                    
                except asyncio.TimeoutError:
                    wait_time = min(5 * (2 ** min(chunk_attempt - 1, 5)), 60)  # Cap at 60s
                    logger.warning(f"[WARN] Chunk {idx + 1} timed out (attempt {chunk_attempt}), retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                    
                except Exception as e:
                    error_msg = str(e)
                    is_rate_limit = (
                        "429" in error_msg or 
                        "rate" in error_msg.lower() or
                        "capacity" in error_msg.lower() or
                        "exceeded" in error_msg.lower()
                    )
                    
                    if is_rate_limit:
                        # Exponential backoff for rate limits: 5s, 10s, 20s, 40s, 60s (capped)
                        wait_time = min(5 * (2 ** min(chunk_attempt - 1, 5)), 60)
                        logger.warning(f"[WARN] Rate limited on chunk {idx + 1} (attempt {chunk_attempt}), waiting {wait_time}s before retry...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        # Other errors - shorter wait
                        wait_time = min(3 * chunk_attempt, 15)  # Cap at 15s
                        logger.warning(f"[WARN] Error on chunk {idx + 1} (attempt {chunk_attempt}): {error_msg}")
                        logger.warning(f"⏳ Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
            
            # Extract endpoints from this chunk (after successful processing)
            chunk_endpoints = chunk_result.get('endpoints', [])
            if chunk_endpoints:
                all_endpoints.extend(chunk_endpoints)
                logger.info(f"[OK] Found {len(chunk_endpoints)} endpoints in chunk {idx + 1}")
            
            # Extract base URL (use first one found)
            if not base_url and chunk_result.get('base_url'):
                base_url = chunk_result['base_url']
                logger.info(f"[OK] Found base URL: {base_url}")
            
            # Extract auth info (use first one found)
            if not auth_info and chunk_result.get('auth'):
                auth_info = chunk_result['auth']
                logger.info(f"[OK] Found auth info: {auth_info.get('type')}")
            
            # Extract title (use first one found)
            if title == "API Documentation" and chunk_result.get('title'):
                title = chunk_result['title']
            
            # Add delay between chunks to avoid rate limiting
            if idx < len(chunks) - 1:
                await asyncio.sleep(3)  # Increased delay between chunks
        
        logger.info(f"[OK] Chunked analysis complete: {len(all_endpoints)} total endpoints found")
        
        return {
            "title": title,
            "version": "1.0.0",
            "description": f"{description}. Found {len(all_endpoints)} endpoints across {len(chunks)} document sections.",
            "base_url": base_url or "https://api.example.com",
            "auth": auth_info,
            "endpoints": all_endpoints,
            "schemas": {},
            "workflows": {}
        }
    
    def _convert_to_api_spec(self, data: Dict[str, Any]) -> APISpecification:
        """Convert extracted data to APISpecification object"""
        
        # Parse authentication
        auth_config = None
        if "auth" in data and data["auth"]:
            auth_data = data["auth"]
            auth_type_str = auth_data.get("type", "none").lower()
            
            if auth_type_str == "api_key":
                auth_config = AuthConfig(
                    type=AuthType.API_KEY,
                    header_name=auth_data.get("details", {}).get("header_name") or auth_data.get("header_name")
                )
            elif auth_type_str == "bearer":
                auth_config = AuthConfig(
                    type=AuthType.BEARER_TOKEN,
                    scheme="bearer"
                )
            elif auth_type_str == "oauth2":
                auth_config = AuthConfig(
                    type=AuthType.OAUTH2,
                    flows=auth_data.get("details", {}).get("flows") or {}
                )
            elif auth_type_str == "basic":
                auth_config = AuthConfig(
                    type=AuthType.BASIC_AUTH,
                    scheme="basic"
                )
        
        # Parse endpoints
        endpoints = []
        for endpoint_data in data.get("endpoints", []):
            try:
                # Parse parameters
                parameters = []
                for param_data in endpoint_data.get("parameters", []):
                    location_str = param_data.get("location", "query").lower()
                    param_location = ParameterLocation.QUERY
                    
                    if location_str == "path":
                        param_location = ParameterLocation.PATH
                    elif location_str == "header":
                        param_location = ParameterLocation.HEADER
                    elif location_str == "body":
                        param_location = ParameterLocation.BODY
                    
                    parameters.append(APIParameter(
                        name=param_data.get("name", ""),
                        location=param_location,
                        required=param_data.get("required", False),
                        type=param_data.get("type", "string"),
                        description=param_data.get("description")
                    ))
                
                # Create endpoint
                method_str = endpoint_data.get("method", "GET").upper()
                endpoint = APIEndpoint(
                    path=endpoint_data.get("path", ""),
                    method=HTTPMethod(method_str),
                    summary=endpoint_data.get("summary"),
                    description=endpoint_data.get("description"),
                    parameters=parameters,
                    request_body_schema=endpoint_data.get("request_body"),
                    response_schema=endpoint_data.get("response"),
                    auth_required=endpoint_data.get("auth_required", True)
                )
                
                endpoints.append(endpoint)
            
            except Exception as e:
                logger.warning(f"Error parsing endpoint: {e}")
                continue
        
        # Create APISpecification
        return APISpecification(
            title=data.get("title", "Unnamed API"),
            version=data.get("version", "1.0.0"),
            description=data.get("description"),
            base_url=data.get("base_url", "https://api.example.com"),
            servers=[data.get("base_url")] if data.get("base_url") else [],
            endpoints=endpoints,
            auth=auth_config,
            schemas=data.get("schemas", {}),
            webhooks=data.get("workflows", {})
        )


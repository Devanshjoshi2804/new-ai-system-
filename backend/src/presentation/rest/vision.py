"""
Vision OCR API endpoint using Mistral - Enhanced with GST Extraction
"""
import logging
import base64
import re
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, File, UploadFile
from pydantic import BaseModel

from src.infrastructure.ai.providers.mistral_provider import MistralProvider
from src.infrastructure.ai.pdf_converter import get_pdf_converter

logger = logging.getLogger(__name__)

router = APIRouter()


class VisionRequest(BaseModel):
    """Vision OCR request"""
    imageBase64: str
    prompt: Optional[str] = "Extract all text and data from this image"
    model: Optional[str] = "pixtral-12b-2409"


class VisionResponse(BaseModel):
    """Vision OCR response"""
    success: bool
    content: str
    fileType: str
    usage: Optional[dict] = None
    model: Optional[str] = None


class GSTExtractionRequest(BaseModel):
    """GST document extraction request"""
    documentBase64: str
    extractionMode: Optional[str] = "intelligent"  # intelligent, regex, ai


class GSTExtractionResponse(BaseModel):
    """GST extraction response"""
    success: bool
    gstData: Dict[str, Any]
    extractionMethod: str
    rawText: Optional[str] = None


@router.post("/vision", response_model=VisionResponse)
async def process_vision_ocr(request: VisionRequest):
    """
    Process image/PDF with Mistral Vision API for OCR
    
    Accepts base64 encoded images (data:image/...) or PDFs (data:application/pdf;...)
    """
    try:
        logger.info("[FILE] Processing Vision OCR request")
        
        if not request.imageBase64:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No image provided"
            )
        
        # Detect file type
        is_pdf = request.imageBase64.startswith('data:application/pdf')
        file_type = "PDF" if is_pdf else "Image"
        size_kb = len(request.imageBase64) // 1024
        
        logger.info(f"[INFO] Processing {file_type}, size: {size_kb} KB")
        logger.info(f"[NOTE] Prompt length: {len(request.prompt or '')} characters")
        
        # Extract base64 data (remove data URI prefix)
        if ',' in request.imageBase64:
            base64_data = request.imageBase64.split(',', 1)[1]
        else:
            base64_data = request.imageBase64
        
        # Decode base64 to bytes
        image_bytes = base64.b64decode(base64_data)
        
        # Use Mistral provider
        mistral = MistralProvider()
        
        # For vision tasks, we use the pixtral model
        from mistralai import Mistral
        
        client = Mistral(api_key=mistral.api_key)
        
        # Call Mistral Vision API
        response = client.chat.complete(
            model=request.model or "pixtral-12b-2409",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": request.prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": request.imageBase64
                    }
                ]
            }],
            max_tokens=2000
        )
        
        content = response.choices[0].message.content
        
        logger.info(f"[OK] {file_type} processed successfully!")
        
        return VisionResponse(
            success=True,
            content=content,
            fileType=file_type,
            usage=response.usage.dict() if hasattr(response, 'usage') else None,
            model=response.model if hasattr(response, 'model') else request.model
        )
    
    except Exception as e:
        logger.error(f"[ERROR] Vision OCR error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vision OCR failed: {str(e)}"
        )


@router.post("/vision/extract-gst", response_model=GSTExtractionResponse)
async def extract_gst_data(request: GSTExtractionRequest):
    """
    Intelligently extract GST data from document
    
    Uses hybrid approach:
    1. Regex-based extraction (fast, always works)
    2. AI enhancement with Mistral Vision (if available)
    """
    try:
        logger.info("[INFO] Starting intelligent GST extraction...")
        
        # Convert base64 to bytes
        document_bytes = _base64_to_bytes(request.documentBase64)
        
        # Use Mistral provider
        mistral = MistralProvider()
        
        # Extract text first (for regex)
        text_response = await mistral.process_document(
            document_bytes=document_bytes,
            prompt="Extract all text from this GST certificate. Include all details, names, numbers, and addresses."
        )
        
        text = text_response.get("text", "")
        
        # Step 1: Regex-based extraction (always works)
        regex_data = _extract_gst_with_regex(text)
        logger.info(f"[INFO] Regex extraction: GSTIN={'[OK]' if regex_data.get('gstin') else '[ERROR]'}, Name={'[OK]' if regex_data.get('legalName') else '[ERROR]'}")
        
        extraction_method = "regex"
        final_data = regex_data
        
        # Step 2: AI enhancement (if mode is intelligent or ai)
        if request.extractionMode in ["intelligent", "ai"]:
            try:
                logger.info("[AI] Attempting AI enhancement...")
                ai_data = await _enhance_with_mistral_ai(document_bytes, mistral)
                
                if ai_data:
                    # Merge: AI takes precedence, regex as fallback
                    final_data = _merge_extraction_data(ai_data, regex_data)
                    extraction_method = "ai_enhanced"
                    logger.info("[INFO] AI-enhanced extraction successful!")
                    
            except Exception as ai_error:
                logger.warning(f"[WARN] AI enhancement failed: {ai_error}, using regex data")
        
        return GSTExtractionResponse(
            success=True,
            gstData=final_data,
            extractionMethod=extraction_method,
            rawText=text[:500] if text else None  # Include sample of raw text
        )
        
    except Exception as e:
        logger.error(f"[ERROR] GST extraction error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Extraction error: {str(e)}"
        )


@router.post("/vision/upload-document")
async def upload_and_extract_document(
    file: UploadFile = File(...),
    extraction_type: Optional[str] = "gst",
    process_all_pages: Optional[bool] = True,
    max_pages: Optional[int] = 10
):
    """
    Upload document file and extract data
    
    Supports:
    - PDF files (converted to images for better OCR)
    - Image files (JPG, PNG)
    """
    try:
        # Read file content
        content = await file.read()
        content_type = file.content_type or ""
        
        logger.info(f"[FILE] Uploaded: {file.filename}, type: {content_type}, size: {len(content)} bytes")
        
        # Check if PDF
        is_pdf = "pdf" in content_type.lower() or file.filename.lower().endswith('.pdf')
        
        if is_pdf:
            # [OK] NEW: Convert PDF to images first (like working chatbot version)
            logger.info("[INFO] Converting PDF to images...")
            
            try:
                pdf_converter = get_pdf_converter(dpi=200)  # 200 DPI for good quality
                page_images = await pdf_converter.convert_pdf_to_images(content)
                
                logger.info(f"[OK] Converted PDF to {len(page_images)} images")
            except Exception as conv_error:
                logger.error(f"[ERROR] PDF conversion failed: {conv_error}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"PDF conversion failed: {str(conv_error)}. Make sure pdf2image and poppler are installed."
                )
            
            # Limit pages if needed
            pages_to_process = min(len(page_images), max_pages) if not process_all_pages else len(page_images)
            page_images = page_images[:pages_to_process]
            
            # Process pages based on extraction type
            if extraction_type == "gst":
                # Extract GST data from all pages
                logger.info(f"[INFO] Extracting GST data from {pages_to_process} page(s)")
                all_results = []
                
                for i, page_image in enumerate(page_images):
                    logger.info(f"[FILE] Processing page {i+1}/{pages_to_process}")
                    
                    request = GSTExtractionRequest(
                        documentBase64=page_image,
                        extractionMode="intelligent"
                    )
                    result = await extract_gst_data(request)
                    all_results.append({
                        "page": i + 1,
                        "data": result.gstData,
                        "rawText": result.rawText
                    })
                
                # Merge results from all pages
                merged_data = _merge_multipage_gst_data(all_results)
                
                logger.info(f"[OK] GST extraction complete! GSTIN: {merged_data.get('gstin', 'N/A')}")
                
                return GSTExtractionResponse(
                    success=True,
                    gstData=merged_data,
                    extractionMethod="intelligent_multipage",
                    rawText="\n\n".join([f"=== PAGE {r['page']} ===\n{r['rawText']}" for r in all_results if r.get("rawText")])
                )
            else:
                # Generic OCR for all pages
                logger.info(f"[NOTE] Performing OCR on {pages_to_process} page(s)")
                all_text = []
                
                for i, page_image in enumerate(page_images):
                    logger.info(f"[FILE] OCR page {i+1}/{pages_to_process}")
                    
                    request = VisionRequest(
                        imageBase64=page_image,
                        prompt="Extract all text and structured data from this document page"
                    )
                    result = await process_vision_ocr(request)
                    all_text.append(f"=== PAGE {i+1} ===\n{result.content}")
                
                combined_text = "\n\n".join(all_text)
                logger.info(f"[OK] OCR complete! Extracted {len(combined_text)} characters")
                
                return VisionResponse(
                    success=True,
                    content=combined_text,
                    fileType=f"PDF ({pages_to_process} pages)",
                    model="pixtral-12b-2409"
                )
        else:
            # Image file - process directly (no conversion needed)
            logger.info("[INFO] Processing image file directly")
            base64_str = base64.b64encode(content).decode('utf-8')
            base64_str = f"data:image/png;base64,{base64_str}"
            
            if extraction_type == "gst":
                request = GSTExtractionRequest(
                    documentBase64=base64_str,
                    extractionMode="intelligent"
                )
                return await extract_gst_data(request)
            else:
                request = VisionRequest(
                    imageBase64=base64_str,
                    prompt="Extract all text and structured data from this document"
                )
                return await process_vision_ocr(request)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Upload error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload error: {str(e)}"
        )


# ===============================================
# HELPER FUNCTIONS
# ===============================================

def _base64_to_bytes(base64_string: str) -> bytes:
    """Convert base64 string to bytes"""
    # Remove data URL prefix if present
    if ',' in base64_string:
        base64_string = base64_string.split(',', 1)[1]
    
    return base64.b64decode(base64_string)


def _extract_gst_with_regex(text: str) -> Dict[str, Any]:
    """
    Pattern-based GST extraction (fast, works offline)
    Based on: try and error api try/onboarding-kyc-flow.js:extractGSTWithRegex
    """
    gst_data = {
        "gstin": "",
        "legalName": "",
        "tradeName": "",
        "constitution": "",
        "address": {
            "line1": "",
            "line2": "",
            "city": "",
            "state": "",
            "pincode": "",
            "country": "India"
        },
        "directors": [],
        "issueDate": "",
        "validityDate": ""
    }
    
    # Check if Vision API formatted output (numbered list format)
    is_vision_format = bool(re.search(r'\d+\.\s*\*?\*?(?:GSTIN|Legal\s*Name|Trade\s*Name)', text, re.I))
    
    if is_vision_format:
        logger.info("[INFO] Detected Vision API formatted output")
        return _parse_vision_api_format(text)
    
    # Extract GSTIN (15-character format: 2 digits + 5 letters + 4 digits + 1 letter + 1 digit/letter + Z + 1 alphanumeric)
    gstin_match = re.search(r'(?:GSTIN|GST\s*No|Registration\s*No)[:\s]*([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})', text, re.I)
    if gstin_match:
        gst_data["gstin"] = gstin_match.group(1)
    
    # Extract Legal Name
    legal_name_match = re.search(r'(?:Legal\s*Name|company\s*legal\s*name)[:\s]*([^\n]+)', text, re.I)
    if legal_name_match:
        gst_data["legalName"] = legal_name_match.group(1).strip().lstrip(':').strip()
    
    # Extract Trade Name
    trade_name_match = re.search(r'(?:Trade\s*Name)[:\s]*([^\n]+)', text, re.I)
    if trade_name_match:
        gst_data["tradeName"] = trade_name_match.group(1).strip().lstrip(':').strip()
    else:
        gst_data["tradeName"] = gst_data["legalName"]
    
    # Extract Constitution
    constitution_match = re.search(r'(?:Constitution\s*of\s*Business)[:\s]*([^\n]+)', text, re.I)
    if constitution_match:
        gst_data["constitution"] = constitution_match.group(1).strip().lstrip(':').strip()
    
    # Extract City
    city_match = re.search(r'(?:City)[:\s]*([^\n,]+)', text, re.I)
    if city_match:
        gst_data["address"]["city"] = city_match.group(1).strip()
    
    # Extract State
    state_match = re.search(r'(?:State)[:\s]*([^\n,]+)', text, re.I)
    if state_match:
        gst_data["address"]["state"] = state_match.group(1).strip()
    
    # Extract Pincode
    pincode_match = re.search(r'(?:PIN|Pincode|Pin\s*Code)[:\s]*(\d{6})', text, re.I)
    if pincode_match:
        gst_data["address"]["pincode"] = pincode_match.group(1)
    
    # Extract Directors/Partners
    director_matches = re.findall(r'([A-Z][A-Z\s]{2,30})\s*-?\s*(?:Director|Partner|Proprietor)', text, re.I)
    if director_matches:
        gst_data["directors"] = [
            d.replace(re.search(r'\s*-?\s*(?:Director|Partner|Proprietor)', d, re.I).group(0) if re.search(r'\s*-?\s*(?:Director|Partner|Proprietor)', d, re.I) else '', '').strip()
            for d in director_matches[:5]
        ]
    
    # Extract dates
    date_match = re.search(r'(?:Date\s*of\s*Issue|Issued\s*on)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})', text, re.I)
    if date_match:
        gst_data["issueDate"] = date_match.group(1)
    
    return gst_data


def _parse_vision_api_format(text: str) -> Dict[str, Any]:
    """
    Parse Vision API formatted output (numbered list format)
    Based on: try and error api try/onboarding-kyc-flow.js:parseVisionAPIFormat
    """
    gst_data = {
        "gstin": "",
        "legalName": "",
        "tradeName": "",
        "constitution": "",
        "address": {
            "line1": "",
            "line2": "",
            "city": "",
            "state": "",
            "pincode": "",
            "country": "India"
        },
        "directors": [],
        "issueDate": "",
        "validityDate": ""
    }
    
    # Extract GSTIN - simplified to match any 15-character alphanumeric starting with 2 digits
    gstin_pattern = r'\b([0-9]{2}[A-Z0-9]{13})\b'
    gstin_match = re.search(gstin_pattern, text)
    if gstin_match:
        gst_data["gstin"] = gstin_match.group(1)
        logger.info(f"[OK] GSTIN extracted: {gst_data['gstin']}")
    else:
        logger.warning("[ERROR] GSTIN not found in text")
    
    # Extract Legal Name (handle markdown bold **text**)
    legal_name_match = re.search(
        r'(?:Legal\s*Name|company\s*legal\s*name)[:\s*()]*\*?\*?[:\s]*([A-Z][A-Z\s&]+(?:PRIVATE|PUBLIC|LIMITED|LLP|PARTNERSHIP|PROPRIETORSHIP|Power|And|Ispat)[A-Z\s]*)', 
        text, re.I
    )
    if legal_name_match:
        gst_data["legalName"] = legal_name_match.group(1).replace('**', '').replace('(company legal name):', '').lstrip(':*() ').strip()
    
    # Extract Trade Name (handle markdown and clean up ", if any")
    trade_name_match = re.search(
        r'(?:Trade\s*Name)[:\s*()]*\*?\*?[:\s]*([A-Z][A-Z\s&.,]+(?:PRIVATE|PUBLIC|LIMITED|LLP|PARTNERSHIP|PROPRIETORSHIP|Unit|Of|Ltd|Power|And|Ispat)[A-Z\s.]*)', 
        text, re.I
    )
    if trade_name_match:
        gst_data["tradeName"] = trade_name_match.group(1).replace('**', '').replace(', if any', '').lstrip(':*() ').strip()
    else:
        gst_data["tradeName"] = gst_data["legalName"]
    
    # Extract Constitution (handle markdown)
    constitution_match = re.search(
        r'(?:Constitution\s*of\s*Business)[:\s*()]*\*?\*?[:\s]*([A-Za-z\s]+(?:Company|Partnership|Proprietorship|LLP))', 
        text, re.I
    )
    if constitution_match:
        gst_data["constitution"] = constitution_match.group(1).replace('**', '').lstrip(':*() ').strip()
    
    # Extract Address components
    city_match = re.search(r'(?:City\/Town\/Village)[:\s]*([^\n]+)', text, re.I)
    if city_match:
        gst_data["address"]["city"] = city_match.group(1).strip()
        gst_data["address"]["line2"] = city_match.group(1).strip()
    
    state_match = re.search(r'(?:State)[:\s]*([^\n]+)', text, re.I)
    if state_match:
        gst_data["address"]["state"] = state_match.group(1).strip()
    
    pincode_match = re.search(r'(?:PIN\s*Code)[:\s]*(\d{6})', text, re.I)
    if pincode_match:
        gst_data["address"]["pincode"] = pincode_match.group(1)
    
    # Extract Directors - improved to handle Vision API format across all pages
    name_matches = re.finditer(
        r'[-•]\s*\*?\*?Name\*?\*?[:\s]*([A-Z][A-Z\s]+?)(?=\s*[-\n]|Designation|Status|Resident|Photo)', 
        text, re.I | re.M
    )
    directors_from_bullets = [
        m.group(1).strip() 
        for m in name_matches 
        if len(m.group(1).strip()) > 2 and not re.match(r'^(DIRECTOR|STATUS|RESIDENT|DESIGNATION|PHOTO|Not specified)$', m.group(1).strip(), re.I)
    ]
    
    if directors_from_bullets:
        gst_data["directors"] = directors_from_bullets[:10]
        logger.info(f"[OK] Extracted {len(gst_data['directors'])} directors from bullet points")
    else:
        # Fallback: Look for section 6 or "Directors/Partners names"
        directors_match = re.search(r'6\.\s*(?:\*\*)?Directors?\/Partners?\s*names?(?:\*\*)?[:\s]*([^\n]*(?:\n(?!===|\d+\.)[^\n]*)*)', text, re.I)
        
        if directors_match:
            director_text = directors_match.group(1)
            logger.info(f"[INFO] Directors section found (fallback), length: {len(director_text)}")
            
            # Look for any capitalized names
            alt_matches = re.findall(r'([A-Z][A-Z\s]{5,40}?)(?=\s*[-\n]|Designation|Status|Resident|$)', director_text, re.I)
            if alt_matches:
                gst_data["directors"] = [
                    m.strip() 
                    for m in alt_matches 
                    if len(m.strip()) > 5 and not re.match(r'^(DIRECTOR|STATUS|RESIDENT|DESIGNATION|PHOTO|Not specified|Name)$', m.strip(), re.I)
                ][:10]
                logger.info(f"[OK] Extracted {len(gst_data['directors'])} directors (fallback)")
    
    logger.info(f"[OK] Parsed Vision API format: GSTIN={gst_data['gstin']}, Name={gst_data['legalName']}, Directors={len(gst_data['directors'])}")
    
    return gst_data


async def _enhance_with_mistral_ai(document_bytes: bytes, mistral: MistralProvider) -> Optional[Dict[str, Any]]:
    """
    AI-powered extraction using Mistral Vision API
    Based on: try and error api try/onboarding-kyc-flow.js:enhanceWithMistralAI
    """
    prompt = """You are an expert document processor. Extract ALL information from this GST certificate.

Return ONLY valid JSON (no markdown, no explanation) with this exact structure:
{
  "gstin": "15-character GST number",
  "legalName": "Exact legal name of business",
  "tradeName": "Trade name if different",
  "constitution": "Business type (Private Limited Company, Proprietorship, etc.)",
  "address": {
    "line1": "Building, floor, street",
    "line2": "Area, landmark",
    "city": "City name",
    "state": "State name",
    "pincode": "6-digit pincode"
  },
  "directors": ["Full name 1", "Full name 2"],
  "issueDate": "DD/MM/YYYY",
  "validityDate": "DD/MM/YYYY or Not Applicable",
  "district": "District name",
  "registrationType": "Regular/Composition"
}

Extract every director/partner/proprietor name listed. Be precise with field values."""
    
    try:
        response = await mistral.extract_structured_data(
            document_bytes=document_bytes,
            extraction_prompt=prompt
        )
        
        if response and "extracted_data" in response:
            return response["extracted_data"]
        
        # Try to parse from text response
        if response and "text" in response:
            text = response["text"]
            # Try to extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', text) or re.search(r'(\{[\s\S]*\})', text)
            if json_match:
                import json
                return json.loads(json_match.group(1))
        
        return None
        
    except Exception as e:
        logger.error(f"Mistral AI extraction failed: {str(e)}")
        return None


def _merge_extraction_data(ai_data: Dict[str, Any], regex_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge AI and regex extraction results (AI takes precedence)
    Based on: try and error api try/onboarding-kyc-flow.js:extractGSTDataIntelligently
    """
    merged = {
        "gstin": ai_data.get("gstin") or regex_data.get("gstin", ""),
        "legalName": ai_data.get("legalName") or regex_data.get("legalName", ""),
        "tradeName": ai_data.get("tradeName") or regex_data.get("tradeName") or regex_data.get("legalName", ""),
        "constitution": ai_data.get("constitution") or regex_data.get("constitution", ""),
        "address": {
            "line1": (ai_data.get("address", {}).get("line1") or regex_data.get("address", {}).get("line1", "")),
            "line2": (ai_data.get("address", {}).get("line2") or regex_data.get("address", {}).get("line2", "")),
            "city": (ai_data.get("address", {}).get("city") or regex_data.get("address", {}).get("city", "")),
            "state": (ai_data.get("address", {}).get("state") or regex_data.get("address", {}).get("state", "")),
            "pincode": (ai_data.get("address", {}).get("pincode") or regex_data.get("address", {}).get("pincode", "")),
            "country": "India"
        },
        "directors": (ai_data.get("directors", []) if ai_data.get("directors") else regex_data.get("directors", [])),
        "issueDate": ai_data.get("issueDate") or regex_data.get("issueDate", ""),
        "validityDate": ai_data.get("validityDate") or regex_data.get("validityDate", ""),
        "district": ai_data.get("district"),
        "registrationType": ai_data.get("registrationType")
    }
    
    return merged


def _merge_multipage_gst_data(results: list) -> Dict[str, Any]:
    """
    Merge GST data extracted from multiple PDF pages
    
    Args:
        results: List of dicts with 'page', 'data', and 'rawText' keys
        
    Returns:
        Merged GST data dictionary
    """
    merged = {
        "gstin": "",
        "legalName": "",
        "tradeName": "",
        "constitution": "",
        "address": {
            "line1": "",
            "line2": "",
            "city": "",
            "state": "",
            "pincode": "",
            "country": "India"
        },
        "directors": [],
        "issueDate": "",
        "validityDate": "",
        "district": "",
        "registrationType": ""
    }
    
    # Collect all directors (avoid duplicates)
    all_directors = set()
    
    # Take first non-empty value for each field
    for result in results:
        data = result.get("data", {})
        
        # Simple fields - take first non-empty value
        for key in ["gstin", "legalName", "tradeName", "constitution", "issueDate", "validityDate", "district", "registrationType"]:
            if not merged.get(key) and data.get(key):
                merged[key] = data[key]
        
        # Address fields - merge if not already filled
        if data.get("address"):
            addr = data["address"]
            for addr_key in ["line1", "line2", "city", "state", "pincode"]:
                if not merged["address"].get(addr_key) and addr.get(addr_key):
                    merged["address"][addr_key] = addr[addr_key]
        
        # Directors - accumulate from all pages
        if data.get("directors"):
            for director in data["directors"]:
                if director and isinstance(director, str):
                    # Clean up director name
                    director_clean = director.strip()
                    if director_clean and director_clean not in all_directors:
                        all_directors.add(director_clean)
    
    # Convert directors set back to list
    merged["directors"] = sorted(list(all_directors))
    
    logger.info(f"[INFO] Merged data from {len(results)} pages: GSTIN={merged.get('gstin', 'N/A')}, {len(merged['directors'])} directors")
    
    return merged


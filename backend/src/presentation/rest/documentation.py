"""
API Documentation upload endpoints
"""
import logging
import os
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form, Header
from pydantic import BaseModel
from pathlib import Path

# Using MongoDB for all data storage
from src.domain.value_objects.doc_format import DocFormat
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/test-endpoint")
async def test_endpoint():
    """Simple test endpoint"""
    logger.info("[TARGET] TEST ENDPOINT HIT!")
    return {"status": "ok", "message": "Backend is responding"}


class DocumentationUploadResponse(BaseModel):
    """Documentation upload response"""
    documentation_id: str
    filename: str
    file_size: int
    detected_format: str
    format_confidence: float
    parsing_status: str
    message: str


class DocumentationStatusResponse(BaseModel):
    """Documentation parsing status"""
    documentation_id: str
    parsing_status: str
    parsing_progress: int
    parsing_error: Optional[str] = None
    extracted_endpoints_count: int = 0


@router.post("/partners/{partner_id}/documentation", response_model=DocumentationUploadResponse)
async def upload_documentation(
    partner_id: str,
    file: UploadFile = File(...),
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")
):
    """
    Upload API documentation for a partner
    
    Supports:
    - OpenAPI 3.x (JSON/YAML)
    - Swagger 2.0 (JSON/YAML)
    - Postman Collections (JSON)
    - PDFs (with Mistral OCR)
    - Images (PNG, JPG)
    - Markdown
    - Plain text
    """
    try:
        logger.info(f"[INFO] Starting documentation upload for partner: {partner_id}")
        
        # Verify partner exists using MongoDB
        from src.infrastructure.database.mongodb.partner_repository import MongoDBPartnerRepository
        partner_repo = MongoDBPartnerRepository()
        logger.info(f"[INFO] Partner repository initialized")
        
        partner = await partner_repo.get_by_id(partner_id)
        logger.info(f"[INFO] Partner fetched: {partner is not None}")
        
        if not partner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Partner not found"
            )
        
        # Use tenant_id from partner
        tenant_id = partner['tenant_id']
        logger.info(f"[INFO] Tenant ID: {tenant_id}")
        
        # Validate file size
        logger.info(f"[INFO] Reading file: {file.filename}")
        content = await file.read()
        file_size = len(content)
        logger.info(f"[INFO] File read: {file_size} bytes")
        
        if file_size > settings.max_upload_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Max size: {settings.max_upload_size} bytes"
            )
        
        # Save file first
        logger.info(f"[FLOPPY] Preparing to save file...")
        upload_dir = Path(settings.upload_dir) / tenant_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"[INFO] Upload directory created: {upload_dir}")
        
        file_path = upload_dir / file.filename
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        logger.info(f"[INFO] File saved to: {file_path}")
        
        # Detect format by filename and content type (simpler approach)
        from src.domain.value_objects.doc_format import DocFormat
        
        detected_format = DocFormat.UNKNOWN
        confidence = 0.5
        
        # Detect by extension
        filename_lower = file.filename.lower()
        if filename_lower.endswith('.json'):
            detected_format = DocFormat.OPENAPI_30
            confidence = 0.7
        elif filename_lower.endswith(('.yaml', '.yml')):
            detected_format = DocFormat.OPENAPI_30
            confidence = 0.7
        elif filename_lower.endswith('.pdf'):
            detected_format = DocFormat.PDF
            confidence = 0.9
        elif filename_lower.endswith(('.png', '.jpg', '.jpeg')):
            detected_format = DocFormat.PDF  # Treat images as documents for OCR
            confidence = 0.8
        elif filename_lower.endswith('.md'):
            detected_format = DocFormat.MARKDOWN
            confidence = 0.9
        
        logger.info(f"[INFO] Detected format: {detected_format} (confidence: {confidence})")
        
        # Create documentation record in MongoDB
        logger.info(f"[FLOPPY] Creating documentation record in database...")
        import uuid
        from src.infrastructure.database.mongodb.documentation_repository import MongoDBDocumentationRepository
        
        doc_id = str(uuid.uuid4())
        logger.info(f"[INFO] Generated doc_id: {doc_id}")
        
        doc_repo = MongoDBDocumentationRepository()
        doc_data = {
            'id': doc_id,
            'partner_id': partner_id,
            'tenant_id': tenant_id,
            'format': detected_format.value,
            'file_path': str(file_path),
            'parsing_status': 'uploaded',
            'content': None,
            'url': None,
            'parsing_error': None,
            'endpoints': [],
            'schemas': {},
            'metadata': {
                "filename": file.filename,
                "file_size": file_size,
                "content_type": file.content_type or "application/octet-stream",
                "format_confidence": confidence
            }
        }
        await doc_repo.create(doc_data)
        logger.info(f"[INFO] Documentation record created")
        
        logger.info(f"[OK] Documentation uploaded: {file.filename} (doc_id: {doc_id})")
        
        # Update partner onboarding step
        logger.info(f"[NOTE] Updating partner onboarding step...")
        await partner_repo.update(partner_id, {
            'onboarding_step': 1,
            'status': 'parsing'
        })
        logger.info(f"[INFO] Partner updated")
        
        # TODO: Trigger async parsing task
        # await parse_documentation_task.delay(str(doc.id))
        
        return DocumentationUploadResponse(
            documentation_id=doc_id,
            filename=file.filename,
            file_size=file_size,
            detected_format=detected_format.value,
            format_confidence=confidence,
            parsing_status="uploaded",
            message="Documentation uploaded successfully. Parsing will begin shortly."
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading documentation: {e}", exc_info=True)
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload documentation: {str(e)}"
        )


@router.get("/documentation/{doc_id}/status", response_model=DocumentationStatusResponse)
async def get_documentation_status(doc_id: str):
    """Get documentation parsing status"""
    try:
        from src.infrastructure.database.mongodb.documentation_repository import MongoDBDocumentationRepository
        
        doc_repo = MongoDBDocumentationRepository()
        doc = await doc_repo.get_by_id(doc_id)
        
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Documentation not found"
            )
        
        return DocumentationStatusResponse(
            documentation_id=doc['id'],
            parsing_status=doc.get('parsing_status', 'unknown'),
            parsing_progress=doc.get('parsing_progress', 0),
            parsing_error=doc.get('parsing_error'),
            extracted_endpoints_count=doc.get('extracted_endpoints_count', 0)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting documentation status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/documentation/{doc_id}/parse")
async def trigger_parsing(doc_id: str):
    """
    Manually trigger documentation parsing
    (Normally done automatically after upload)
    """
    logger.info(f"[SEARCH] Parse endpoint called for doc_id: {doc_id}")
    
    try:
        # Get document from MongoDB
        from src.infrastructure.database.mongodb.documentation_repository import MongoDBDocumentationRepository
        
        logger.info(f"[INFO] Fetching document from database...")
        
        doc_repo = MongoDBDocumentationRepository()
        doc = await doc_repo.get_by_id(doc_id)
        
        if not doc:
            logger.error(f"[ERROR] Documentation not found: {doc_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Documentation not found"
            )
        
        logger.info(f"[OK] Document found - ID: {doc['id']}, Format: {doc['format']}")
        
        # Mark as parsing
        logger.info(f"[NOTE] Updating status to 'parsing'...")
        await doc_repo.update_parsing_status(doc_id, 'parsing', 10)
        logger.info(f"[OK] Status updated to 'parsing'")
        
        # Get file path
        file_path = doc.get('file_path')
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Documentation file not found on disk"
            )
        
        logger.info(f"[FILE] Processing file: {file_path}")
        logger.info(f"[INFO] Format: {doc['format']}")
        
        # Parse based on format using actual parsers
        try:
            from src.application.ai.parsers.format_detector import FormatDetector
            from src.application.ai.parsers.multi_parser import MultiParser
            from src.application.ai.parsers.pdf_parser import PDFParser
            from src.application.ai.parsers.image_parser import ImageParser
            from fastapi import UploadFile
            import io
            
            # Read file for parsing
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Create UploadFile object for parsers
            upload_file = UploadFile(
                filename=doc.get('metadata', {}).get('filename', 'document'),
                file=io.BytesIO(file_content)
            )
            
            doc_format = doc['format']
            api_specification = None
            
            # Route to appropriate parser
            if doc_format in ['openapi_30', 'openapi_31', 'swagger_20']:
                logger.info(f"[SEARCH] Using Multi parser (OpenAPI/JSON/YAML/cURL)...")
                await doc_repo.update_parsing_status(doc_id, 'parsing', 30)
                parser = MultiParser()
                api_specification = await parser.parse(upload_file)
                
            elif doc_format == 'pdf':
                logger.info(f"[SEARCH] Using PDF parser with OCR...")
                await doc_repo.update_parsing_status(doc_id, 'parsing', 20)
                parser = PDFParser()
                api_specification = await parser.parse(upload_file)
                
            elif doc_format in ['image', 'png', 'jpg', 'jpeg']:
                logger.info(f"[SEARCH] Using Image parser with OCR...")
                await doc_repo.update_parsing_status(doc_id, 'parsing', 20)
                parser = ImageParser()
                api_specification = await parser.parse(upload_file)
                
            else:
                # Try auto-detection
                logger.info(f"[SEARCH] Auto-detecting format and parsing...")
                await doc_repo.update_parsing_status(doc_id, 'parsing', 20)
                
                # Check file extension first
                filename = upload_file.filename or ""
                file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
                
                if file_ext in ['json', 'yaml', 'yml', 'txt']:
                    # JSON, YAML, or text files go to MultiParser
                    logger.info(f"[OK] File extension '{file_ext}' - using MultiParser")
                    parser = MultiParser()
                elif file_ext == 'pdf':
                    logger.info(f"[OK] File extension 'pdf' - using PDFParser")
                    parser = PDFParser()
                elif file_ext in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
                    logger.info(f"[OK] File extension '{file_ext}' - using ImageParser")
                    parser = ImageParser()
                else:
                    # Fall back to content detection
                    detector = FormatDetector()
                    await upload_file.seek(0)
                    detected_format, confidence = await detector.detect(upload_file)
                    logger.info(f"[OK] Detected format: {detected_format} (confidence: {confidence})")
                    
                    if detected_format.value == 'pdf':
                        parser = PDFParser()
                    elif detected_format.value in ['openapi_30', 'openapi_31', 'swagger_20']:
                        parser = MultiParser()
                    else:
                        parser = ImageParser()
                
                await upload_file.seek(0)
                api_specification = await parser.parse(upload_file)
            
            await doc_repo.update_parsing_status(doc_id, 'parsing', 80)
            
            # Convert APISpecification to dict
            endpoints_list = [
                {
                    "path": ep.path,
                    "method": ep.method.value,
                    "summary": ep.summary or "",
                    "description": ep.description or "",
                    "parameters": [
                        {
                            "name": p.name,
                            "location": p.location.value,
                            "required": p.required,
                            "type": p.type,
                            "description": p.description
                        }
                        for p in (ep.parameters or [])
                    ],
                    "auth_required": ep.auth_required
                }
                for ep in (api_specification.endpoints or [])
            ]
            
            api_spec = {
                "title": api_specification.title,
                "version": api_specification.version,
                "description": api_specification.description,
                "baseUrl": api_specification.base_url,
                "endpoints": endpoints_list,
                "auth": {
                    "type": api_specification.auth.type.value if api_specification.auth else "none",
                    "details": {}
                } if api_specification.auth else None,
                "schemas": api_specification.schemas or {}
            }
            
            logger.info(f"[OK] Extracted {len(endpoints_list)} endpoints")
            
            # Save parsed data
            await doc_repo.update_parsed_data(doc_id, api_spec, len(endpoints_list))
            await doc_repo.update_parsing_status(doc_id, 'completed', 100)
            
            logger.info(f"[OK] Parsing completed successfully!")
            
            response_data = {
                "id": doc_id,
                "status": "completed",
                "format": doc['format'],
                "message": f"Parsing completed successfully using {parser.__class__.__name__}",
                "api_spec": api_spec,
                "workflows": []
            }
            
            logger.info(f"[INFO] Returning response with {len(endpoints_list)} real endpoints")
            return response_data
            
        except Exception as parse_error:
            logger.error(f"[ERROR] Parsing error: {parse_error}", exc_info=True)
            await doc_repo.update_parsing_status(doc_id, 'failed', 100, str(parse_error))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to parse documentation: {str(parse_error)}"
            )
    
    except HTTPException as http_ex:
        logger.error(f"[ERROR] HTTP Exception: {http_ex.detail}")
        raise
    except Exception as e:
        logger.error(f"[ERROR] Unexpected error in parse endpoint: {e}", exc_info=True)
        
        # Mark as failed
        try:
            from src.infrastructure.database.mongodb.documentation_repository import MongoDBDocumentationRepository
            doc_repo = MongoDBDocumentationRepository()
            await doc_repo.update_parsing_status(doc_id, 'failed', 100, str(e))
        except Exception as update_error:
            logger.error(f"[ERROR] Failed to update error status: {update_error}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse documentation: {str(e)}"
        )


@router.post("/documentation/analyze-multiple")
async def analyze_multiple_documents(doc_ids: list[str]):
    """
    Analyze MULTIPLE documents together - combine all extracted text and analyze as one
    This is used when user uploads multiple sources (PDF + JSON + cURL, etc.)
    """
    logger.info(f"[INFO] AI Analysis endpoint called for {len(doc_ids)} documents")
    
    try:
        from src.infrastructure.database.mongodb.documentation_repository import MongoDBDocumentationRepository
        
        doc_repo = MongoDBDocumentationRepository()
        
        # Collect all extracted text from all documents
        combined_text = ""
        all_extraction_methods = []
        total_chars = 0
        
        for doc_id in doc_ids:
            doc = await doc_repo.get_by_id(doc_id)
            
            if not doc:
                logger.warning(f"[WARN] Document not found: {doc_id}, skipping...")
                continue
            
            api_spec = doc.get('api_spec', {})
            extracted_text = api_spec.get('schemas', {}).get('extracted_text', {}) or api_spec.get('schemas', {}).get('_ocr_metadata', {})
            
            if extracted_text and extracted_text.get('full_text'):
                text = extracted_text['full_text']
                method = extracted_text.get('extraction_method', 'Unknown')
                
                combined_text += f"\n\n=== Document {doc_id} ({method}) ===\n\n{text}"
                all_extraction_methods.append(method)
                total_chars += len(text)
                logger.info(f"[OK] Added {len(text)} chars from {doc_id} ({method})")
        
        if not combined_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No extracted text found in any of the documents"
            )
        
        logger.info(f"[INFO] Combined {len(doc_ids)} documents: {total_chars} total characters")
        logger.info("[INFO] Starting AI analysis on combined text...")
        
        # Determine which parser to use (use first extraction method)
        extraction_method = all_extraction_methods[0] if all_extraction_methods else 'PyMuPDF4LLM'
        
        if extraction_method in ['JSON', 'YAML', 'cURL', 'MultiParser']:
            from src.application.ai.parsers.multi_parser import MultiParser
            parser = MultiParser()
            logger.info(f"[SEARCH] Using MultiParser for combined analysis")
        else:
            from src.application.ai.parsers.pdf_parser import PDFParser
            parser = PDFParser()
            logger.info(f"[SEARCH] Using PDFParser for combined analysis")
        
        # Analyze combined text
        combined_extracted_data = {
            "full_text": combined_text,
            "total_characters": total_chars,
            "source_documents": doc_ids,
            "extraction_methods": all_extraction_methods
        }
        
        api_spec_converted = await parser.analyze_extracted_text(combined_extracted_data)
        
        logger.info(f"[OK] Combined AI analysis complete: {len(api_spec_converted.endpoints)} endpoints found")
        
        # Convert to dict
        endpoints_list = [
            {
                "path": ep.path,
                "method": ep.method.value,
                "summary": ep.summary or "",
                "description": ep.description or "",
                "parameters": [
                    {
                        "name": p.name,
                        "location": p.location.value,
                        "required": p.required,
                        "type": p.type,
                        "description": p.description
                    }
                    for p in (ep.parameters or [])
                ],
                "auth_required": ep.auth_required
            }
            for ep in (api_spec_converted.endpoints or [])
        ]
        
        final_api_spec = {
            "title": api_spec_converted.title,
            "version": api_spec_converted.version,
            "description": f"{api_spec_converted.description} (Combined from {len(doc_ids)} sources)",
            "baseUrl": api_spec_converted.base_url,
            "endpoints": endpoints_list,
            "auth": {
                "type": api_spec_converted.auth.type.value if api_spec_converted.auth else "none",
                "details": {}
            } if api_spec_converted.auth else None,
            "schemas": {
                **api_spec_converted.schemas,
                "source_documents": doc_ids,
                "combined_analysis": True
            }
        }
        
        # Save to the FIRST document
        primary_doc_id = doc_ids[0]
        await doc_repo.update_parsed_data(primary_doc_id, final_api_spec, len(endpoints_list))
        await doc_repo.update_parsing_status(primary_doc_id, 'completed', 100)
        
        logger.info(f"[FLOPPY] Saved combined analysis to primary document: {primary_doc_id}")
        
        return {
            "id": primary_doc_id,
            "status": "completed",
            "message": f"Successfully analyzed {len(doc_ids)} documents together",
            "combined_documents": doc_ids,
            "api_spec": final_api_spec
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Error in combined analysis: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze documents: {str(e)}"
        )


@router.post("/documentation/{doc_id}/analyze")
async def analyze_with_ai(doc_id: str):
    """
    Trigger AI analysis on already-extracted OCR text
    This is called AFTER OCR extraction to analyze and extract API endpoints
    """
    logger.info(f"[INFO] AI Analysis endpoint called for doc_id: {doc_id}")
    
    try:
        # Get document from MongoDB
        from src.infrastructure.database.mongodb.documentation_repository import MongoDBDocumentationRepository
        
        doc_repo = MongoDBDocumentationRepository()
        doc = await doc_repo.get_by_id(doc_id)
        
        if not doc:
            logger.error(f"[ERROR] Documentation not found: {doc_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Documentation not found"
            )
        
        logger.info(f"[OK] Document found - checking for extracted text...")
        
        # Check if document has extracted text
        api_spec = doc.get('api_spec', {})
        extracted_text = api_spec.get('schemas', {}).get('extracted_text', {}) or api_spec.get('schemas', {}).get('_ocr_metadata', {})
        
        if not extracted_text or not extracted_text.get('full_text'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No extracted text found. Please parse the document first."
            )
        
        # Check if already analyzed
        if extracted_text.get('ai_analysis_completed', False) or not extracted_text.get('ai_analysis_pending', True):
            logger.info("[WARN] Document already analyzed")
            return {
                "id": doc_id,
                "status": "already_analyzed",
                "message": "Document has already been analyzed",
                "api_spec": api_spec
            }
        
        logger.info(f"[INFO] Found extracted text: {len(extracted_text['full_text'])} characters")
        logger.info("[INFO] Starting AI analysis...")
        
        # Update status to analyzing
        await doc_repo.update_parsing_status(doc_id, 'analyzing', 50)
        
        # Determine which parser to use based on extraction method
        extraction_method = extracted_text.get('extraction_method', 'PyMuPDF4LLM')
        
        if extraction_method in ['JSON', 'YAML', 'cURL', 'MultiParser']:
            # Use MultiParser for JSON/YAML/cURL
            from src.application.ai.parsers.multi_parser import MultiParser
            parser = MultiParser()
            logger.info(f"[SEARCH] Using MultiParser for {extraction_method} analysis")
        else:
            # Use PDFParser for PDF/images
            from src.application.ai.parsers.pdf_parser import PDFParser
            parser = PDFParser()
            logger.info(f"[SEARCH] Using PDFParser for {extraction_method} analysis")
        
        # Analyze extracted text with AI
        try:
            logger.info("[AI] Calling Mistral AI to analyze extracted text...")
            
            # Use the analyze_extracted_text method (both parsers have this)
            api_spec_converted = await parser.analyze_extracted_text(extracted_text)
            
            logger.info(f"[OK] AI analysis complete: {len(api_spec_converted.endpoints)} endpoints found")
            
            # Convert to dict for storage
            endpoints_list = [
                {
                    "path": ep.path,
                    "method": ep.method.value,
                    "summary": ep.summary or "",
                    "description": ep.description or "",
                    "parameters": [
                        {
                            "name": p.name,
                            "location": p.location.value,
                            "required": p.required,
                            "type": p.type,
                            "description": p.description
                        }
                        for p in (ep.parameters or [])
                    ],
                    "auth_required": ep.auth_required
                }
                for ep in (api_spec_converted.endpoints or [])
            ]
            
            final_api_spec = {
                "title": api_spec_converted.title,
                "version": api_spec_converted.version,
                "description": api_spec_converted.description,
                "baseUrl": api_spec_converted.base_url,
                "endpoints": endpoints_list,
                "auth": {
                    "type": api_spec_converted.auth.type.value if api_spec_converted.auth else "none",
                    "details": {}
                } if api_spec_converted.auth else None,
                "schemas": api_spec_converted.schemas or {}
            }
            
            # Save analyzed data
            await doc_repo.update_parsed_data(doc_id, final_api_spec, len(endpoints_list))
            await doc_repo.update_parsing_status(doc_id, 'completed', 100)
            
            logger.info(f"[OK] AI analysis completed and saved!")
            
            return {
                "id": doc_id,
                "status": "completed",
                "message": f"AI analysis completed successfully. Found {len(endpoints_list)} endpoints.",
                "api_spec": final_api_spec,
                "endpoints_found": len(endpoints_list)
            }
            
        except Exception as analysis_error:
            logger.error(f"[ERROR] AI analysis error: {analysis_error}", exc_info=True)
            await doc_repo.update_parsing_status(doc_id, 'analysis_failed', 100, str(analysis_error))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"AI analysis failed: {str(analysis_error)}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Unexpected error in analyze endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze documentation: {str(e)}"
        )


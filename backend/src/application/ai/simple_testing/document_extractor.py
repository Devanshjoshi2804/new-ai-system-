"""
Document Extraction - Extract text from PDF or JSON
"""
import json


async def extract_document(doc_path: str) -> str:
    """Extract text from PDF or JSON"""
    print("\n" + "=" * 80)
    print("[FILE] STEP 1: DOCUMENT EXTRACTION")
    print("=" * 80)
    
    ext = doc_path.lower().split('.')[-1]
    
    if ext == 'pdf':
        print(f"[INFO] Loading PDF: {doc_path}")
        from langchain_pymupdf4llm import PyMuPDF4LLMLoader
        
        loader = PyMuPDF4LLMLoader(doc_path, mode="page")
        docs = loader.load()
        
        print(f"[OK] Extracted {len(docs)} pages")
        
        # Combine all pages
        full_text = "\n\n".join([
            doc.page_content if isinstance(doc.page_content, str) else doc.page_content.get('text', str(doc.page_content))
            for doc in docs
        ])
        
    elif ext == 'json':
        print(f"[INFO] Loading JSON: {doc_path}")
        with open(doc_path, 'r') as f:
            data = json.load(f)
        
        # Convert JSON to readable text
        full_text = json.dumps(data, indent=2, ensure_ascii=False)
        print(f"[OK] Extracted JSON with {len(data)} keys")
    
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    
    print(f"[INFO] Total characters: {len(full_text)}")
    print(f"[NOTE] Preview:\n{full_text[:300]}...")
    
    return full_text



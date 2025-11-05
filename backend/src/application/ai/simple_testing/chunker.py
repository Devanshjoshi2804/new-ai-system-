"""
Text Chunking - Split text into chunks for RAG retrieval
"""


async def chunk_text(full_text: str) -> list:
    """Split text into chunks for RAG retrieval"""
    print("\n" + "=" * 80)
    print("[INFO] STEP 2: TEXT CHUNKING FOR RAG")
    print("=" * 80)
    
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=400,
        length_function=len,
    )
    
    chunks = text_splitter.split_text(full_text)
    print(f"[INFO] Split into {len(chunks)} chunks (2000 chars, 400 overlap)")
    print(f"[OK] Chunks ready for RAG retrieval")
    
    return chunks



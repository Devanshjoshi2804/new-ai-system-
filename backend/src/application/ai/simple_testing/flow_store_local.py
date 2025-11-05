"""
Flow Data Storage - ChromaDB with LOCAL embeddings (NO API CALLS!)
"""
import os
import asyncio
import json
import random
from typing import Dict, Any

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


class FlowDataStore:
    """Store ongoing test flow data in ChromaDB using LOCAL embeddings"""
    
    def __init__(self):
        self.persist_directory = "./data/flow_chroma_db"
        os.makedirs(self.persist_directory, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False, allow_reset=True)
        )
        
        # Use LOCAL sentence transformer - NO API CALLS!
        print("[LOAD] Loading local embedding model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("[OK] Local embedding model loaded")
        
        # Create collection for this test session
        self.collection_name = f"test_flow_{random.randint(100000, 999999)}"
        try:
            self.collection = self.client.create_collection(name=self.collection_name)
        except:
            self.collection = self.client.get_collection(name=self.collection_name)
        
        print(f"[OK] Flow ChromaDB initialized: {self.collection_name} (LOCAL embeddings - no API calls!)")
    
    def store_request(self, endpoint_key: str, request_payload: Dict[str, Any]):
        """Store request payload in ChromaDB"""
        doc_text = f"REQUEST for {endpoint_key}:\n{json.dumps(request_payload, indent=2)}"
        
        # Generate embedding using LOCAL model
        embedding = self.embedding_model.encode(doc_text).tolist()
        
        # Store in ChromaDB
        self.collection.add(
            documents=[doc_text],
            embeddings=[embedding],
            metadatas=[{
                "type": "request",
                "endpoint": endpoint_key,
                "data": json.dumps(request_payload)
            }],
            ids=[f"{endpoint_key}_request_{random.randint(1000, 9999)}"]
        )
        print(f"   [FLOPPY] Stored request in Flow DB: {endpoint_key}")
    
    def store_response(self, endpoint_key: str, response_data: Dict[str, Any]):
        """Store response data in ChromaDB"""
        doc_text = f"RESPONSE from {endpoint_key}:\n{json.dumps(response_data, indent=2)}"
        
        # Generate embedding using LOCAL model
        embedding = self.embedding_model.encode(doc_text).tolist()
        
        # Store in ChromaDB
        self.collection.add(
            documents=[doc_text],
            embeddings=[embedding],
            metadatas=[{
                "type": "response",
                "endpoint": endpoint_key,
                "data": json.dumps(response_data)
            }],
            ids=[f"{endpoint_key}_response_{random.randint(1000, 9999)}"]
        )
        print(f"   [FLOPPY] Stored response in Flow DB: {endpoint_key}")
    
    def query_for_fields(self, query: str, k: int = 3) -> str:
        """Query ChromaDB for relevant previous requests/responses"""
        # Generate query embedding using LOCAL model
        query_embedding = self.embedding_model.encode(query).tolist()
        
        # Search ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k
        )
        
        if not results['documents'] or not results['documents'][0]:
            return "No previous flow data found."
        
        # Combine relevant documents
        combined_text = "\n\n---\n\n".join(results['documents'][0])
        return combined_text
    
    def cleanup(self):
        """Clean up the test session collection"""
        try:
            self.client.delete_collection(name=self.collection_name)
            print(f"[DEL]  Cleaned up Flow DB: {self.collection_name}")
        except Exception as e:
            print(f"[WARN] Could not clean up Flow DB: {e}")



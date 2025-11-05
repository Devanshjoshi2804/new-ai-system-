"""
Gemini Embeddings Provider
Alternative to OpenAI embeddings for vector search
"""
import logging
from typing import List, Union
import google.generativeai as genai

from src.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)


class GeminiEmbeddings:
    """
    Generate embeddings using Google Gemini
    Compatible with Pinecone and other vector stores
    """
    
    def __init__(self):
        settings = get_settings()
        genai.configure(api_key=settings.google_gemini_api_key)
        self.model = "models/embedding-001"  # Gemini embedding model
        logger.info("[OK] Gemini embeddings initialized")
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed multiple documents
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embeddings (each is a list of floats)
        """
        try:
            logger.info(f"[INFO] Generating embeddings for {len(texts)} documents...")
            
            embeddings = []
            for text in texts:
                result = genai.embed_content(
                    model=self.model,
                    content=text,
                    task_type="retrieval_document"
                )
                embeddings.append(result['embedding'])
            
            logger.info(f"[OK] Generated {len(embeddings)} embeddings")
            return embeddings
        
        except Exception as e:
            logger.error(f"[ERROR] Error generating embeddings: {e}")
            # Return dummy embeddings to prevent crashes
            return [[0.0] * 768 for _ in texts]  # Gemini uses 768 dimensions
    
    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query
        
        Args:
            text: Query text to embed
            
        Returns:
            Embedding vector
        """
        try:
            logger.info(f"[SEARCH] Generating query embedding...")
            
            result = genai.embed_content(
                model=self.model,
                content=text,
                task_type="retrieval_query"
            )
            
            logger.info(f"[OK] Generated query embedding")
            return result['embedding']
        
        except Exception as e:
            logger.error(f"[ERROR] Error generating query embedding: {e}")
            # Return dummy embedding to prevent crashes
            return [0.0] * 768  # Gemini uses 768 dimensions


# Global instance
_embeddings: GeminiEmbeddings = None


def get_embeddings() -> GeminiEmbeddings:
    """Get global embeddings instance"""
    global _embeddings
    if _embeddings is None:
        _embeddings = GeminiEmbeddings()
    return _embeddings


"""
Vector DB Monitoring Script
Real-time monitoring of Vector DB health and performance
"""
import asyncio
import time
from datetime import datetime
from typing import Dict, Any
import sys

from src.infrastructure.database.mongodb.connection import MongoDBConnection
from src.infrastructure.ai.vector_store import DocumentVectorStore
from src.infrastructure.config.settings import get_settings


class VectorDBMonitor:
    """Monitor Vector DB health and performance"""
    
    def __init__(self):
        self.settings = get_settings()
        self.vector_store = None
        self.start_time = time.time()
    
    async def initialize(self):
        """Initialize connections"""
        await MongoDBConnection.connect()
        self.vector_store = DocumentVectorStore(
            collection_name=self.settings.vector_db_collection_prefix,
            persist_directory=self.settings.vector_db_persist_dir,
            embedding_model=self.settings.embedding_model
        )
    
    async def get_overview(self) -> Dict[str, Any]:
        """Get overall Vector DB status"""
        health = self.vector_store.health_check()
        
        # Get all documents
        db = MongoDBConnection.get_database()
        collection = db['api_documentation']
        total_docs = await collection.count_documents({})
        docs_with_vector_db = await collection.count_documents({'vector_db_stored': True})
        
        return {
            'health': health,
            'total_documents': total_docs,
            'documents_in_vector_db': docs_with_vector_db,
            'coverage_percentage': (docs_with_vector_db / total_docs * 100) if total_docs > 0 else 0
        }
    
    async def get_document_stats(self) -> list:
        """Get stats for all documents"""
        db = MongoDBConnection.get_database()
        collection = db['api_documentation']
        
        cursor = collection.find({'vector_db_stored': True})
        docs = await cursor.to_list(length=None)
        
        stats = []
        for doc in docs:
            doc_id = doc.get('id')
            vector_stats = self.vector_store.get_stats(doc_id)
            
            stats.append({
                'doc_id': doc_id,
                'filename': doc.get('filename', 'unknown'),
                'partner_id': doc.get('partner_id'),
                'chunks_count': vector_stats.get('chunks_count', 0),
                'exists': vector_stats.get('exists', False)
            })
        
        return stats
    
    def print_header(self):
        """Print monitoring header"""
        print("\n" + "=" * 80)
        print("🧠 VECTOR DB MONITOR")
        print("=" * 80)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Persist Dir: {self.settings.vector_db_persist_dir}")
        print(f"Embedding Model: {self.settings.embedding_model}")
        print("=" * 80 + "\n")
    
    def print_overview(self, overview: Dict[str, Any]):
        """Print overview section"""
        health = overview['health']
        
        print("📊 OVERVIEW")
        print("-" * 80)
        print(f"Health Status:        {health.get('status', 'unknown').upper()}")
        print(f"Collections:          {health.get('collections_count', 0)}")
        print(f"Total Documents:      {overview['total_documents']}")
        print(f"In Vector DB:         {overview['documents_in_vector_db']}")
        print(f"Coverage:             {overview['coverage_percentage']:.1f}%")
        print()
    
    def print_document_stats(self, stats: list):
        """Print document statistics"""
        print("📚 DOCUMENT STATISTICS")
        print("-" * 80)
        
        if not stats:
            print("No documents in Vector DB")
            return
        
        # Header
        print(f"{'Filename':<40} {'Chunks':<10} {'Status':<10}")
        print("-" * 80)
        
        # Documents
        total_chunks = 0
        for stat in stats:
            filename = stat['filename'][:38]
            chunks = stat['chunks_count']
            status = "✅ OK" if stat['exists'] else "❌ Missing"
            
            print(f"{filename:<40} {chunks:<10} {status:<10}")
            total_chunks += chunks
        
        # Summary
        print("-" * 80)
        print(f"Total: {len(stats)} documents, {total_chunks} chunks")
        if len(stats) > 0:
            avg_chunks = total_chunks / len(stats)
            print(f"Average: {avg_chunks:.1f} chunks per document")
        print()
    
    async def run_once(self):
        """Run monitoring once"""
        self.print_header()
        
        # Get overview
        overview = await self.get_overview()
        self.print_overview(overview)
        
        # Get document stats
        stats = await self.get_document_stats()
        self.print_document_stats(stats)
        
        print("=" * 80)
    
    async def run_continuous(self, interval: int = 60):
        """Run monitoring continuously"""
        print(f"🔄 Continuous monitoring (refresh every {interval}s)")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                # Clear screen (works on Unix and Windows)
                print("\033[2J\033[H", end="")
                
                await self.run_once()
                
                print(f"\n⏱️  Next update in {interval}s... (Ctrl+C to stop)")
                await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Monitoring stopped")
    
    async def cleanup(self):
        """Cleanup connections"""
        await MongoDBConnection.disconnect()


async def main():
    """Main monitoring function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor Vector DB')
    parser.add_argument('--continuous', '-c', action='store_true', help='Continuous monitoring')
    parser.add_argument('--interval', '-i', type=int, default=60, help='Update interval in seconds (default: 60)')
    args = parser.parse_args()
    
    monitor = VectorDBMonitor()
    
    try:
        await monitor.initialize()
        
        if args.continuous:
            await monitor.run_continuous(interval=args.interval)
        else:
            await monitor.run_once()
            
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        await monitor.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

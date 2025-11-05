"""
Migration Script: Add Existing Documents to Vector DB
Migrates all existing API documentation to Vector DB
"""
import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime

from src.infrastructure.database.mongodb.connection import MongoDBConnection
from src.infrastructure.database.mongodb.documentation_repository import MongoDBDocumentationRepository
from src.infrastructure.ai.vector_store import DocumentVectorStore
from src.infrastructure.config.settings import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VectorDBMigration:
    """Migrate existing documents to Vector DB"""
    
    def __init__(self):
        self.settings = get_settings()
        self.doc_repo = None
        self.vector_store = None
        self.stats = {
            'total_docs': 0,
            'migrated': 0,
            'failed': 0,
            'skipped': 0,
            'total_chunks': 0
        }
    
    async def initialize(self):
        """Initialize connections"""
        logger.info("🔌 Connecting to MongoDB...")
        await MongoDBConnection.connect()
        
        logger.info("📚 Initializing Document Repository...")
        self.doc_repo = MongoDBDocumentationRepository(enable_vector_db=True)
        self.vector_store = self.doc_repo.get_vector_store()
        
        if not self.vector_store:
            raise Exception("❌ Vector DB not available")
        
        logger.info("✅ Initialization complete")
    
    async def get_all_documents(self) -> List[Dict[str, Any]]:
        """Get all documents from MongoDB"""
        logger.info("📖 Fetching all documents...")
        
        db = MongoDBConnection.get_database()
        collection = db['api_documentation']
        
        cursor = collection.find({})
        docs = await cursor.to_list(length=None)
        
        logger.info(f"✅ Found {len(docs)} documents")
        return docs
    
    async def migrate_document(self, doc: Dict[str, Any]) -> bool:
        """Migrate a single document to Vector DB"""
        doc_id = doc.get('id')
        filename = doc.get('filename', 'unknown')
        
        try:
            # Check if already in Vector DB
            stats = self.vector_store.get_stats(doc_id)
            if stats.get('exists') and stats.get('chunks_count', 0) > 0:
                logger.info(f"⏭️  Skipping {filename} (already in Vector DB with {stats['chunks_count']} chunks)")
                self.stats['skipped'] += 1
                return True
            
            # Get extracted text
            extracted_text = doc.get('extracted_text')
            if not extracted_text:
                logger.warning(f"⚠️  Skipping {filename} (no extracted text)")
                self.stats['skipped'] += 1
                return True
            
            # Store in Vector DB
            logger.info(f"📚 Migrating {filename} (doc_id: {doc_id})...")
            
            result = self.vector_store.store_documentation(
                doc_id=doc_id,
                doc_text=extracted_text,
                metadata={
                    'partner_id': doc.get('partner_id'),
                    'filename': filename,
                    'migrated_at': datetime.utcnow().isoformat()
                }
            )
            
            if result.get('success'):
                chunks_count = result.get('chunks_count', 0)
                logger.info(f"✅ Migrated {filename}: {chunks_count} chunks")
                
                # Update MongoDB with Vector DB info
                await self.doc_repo.update(doc_id, {
                    'vector_db_stored': True,
                    'vector_db_chunks': chunks_count,
                    'vector_db_chars': result.get('total_chars', 0),
                    'vector_db_migrated_at': datetime.utcnow()
                })
                
                self.stats['migrated'] += 1
                self.stats['total_chunks'] += chunks_count
                return True
            else:
                error = result.get('error', 'Unknown error')
                logger.error(f"❌ Failed to migrate {filename}: {error}")
                self.stats['failed'] += 1
                return False
                
        except Exception as e:
            logger.error(f"❌ Error migrating {filename}: {e}", exc_info=True)
            self.stats['failed'] += 1
            return False
    
    async def migrate_all(self, batch_size: int = 5, dry_run: bool = False):
        """Migrate all documents"""
        logger.info("=" * 80)
        logger.info("🚀 VECTOR DB MIGRATION")
        logger.info("=" * 80)
        
        if dry_run:
            logger.info("⚠️  DRY RUN MODE - No changes will be made")
        
        # Initialize
        await self.initialize()
        
        # Get all documents
        docs = await self.get_all_documents()
        self.stats['total_docs'] = len(docs)
        
        if not docs:
            logger.info("ℹ️  No documents to migrate")
            return
        
        logger.info(f"📊 Starting migration of {len(docs)} documents...")
        logger.info(f"⚙️  Batch size: {batch_size}")
        logger.info("")
        
        # Process in batches
        for i in range(0, len(docs), batch_size):
            batch = docs[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(docs) + batch_size - 1) // batch_size
            
            logger.info(f"📦 Processing batch {batch_num}/{total_batches}...")
            
            if dry_run:
                for doc in batch:
                    doc_id = doc.get('id')
                    filename = doc.get('filename', 'unknown')
                    has_text = bool(doc.get('extracted_text'))
                    logger.info(f"   Would migrate: {filename} (has_text: {has_text})")
                self.stats['migrated'] += len(batch)
            else:
                # Migrate batch
                tasks = [self.migrate_document(doc) for doc in batch]
                await asyncio.gather(*tasks)
            
            # Progress update
            progress = min(i + batch_size, len(docs))
            pct = (progress / len(docs)) * 100
            logger.info(f"📈 Progress: {progress}/{len(docs)} ({pct:.1f}%)")
            logger.info("")
        
        # Final report
        logger.info("=" * 80)
        logger.info("📊 MIGRATION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Total documents:     {self.stats['total_docs']}")
        logger.info(f"✅ Migrated:         {self.stats['migrated']}")
        logger.info(f"⏭️  Skipped:          {self.stats['skipped']}")
        logger.info(f"❌ Failed:           {self.stats['failed']}")
        logger.info(f"📚 Total chunks:     {self.stats['total_chunks']}")
        
        if self.stats['migrated'] > 0:
            avg_chunks = self.stats['total_chunks'] / self.stats['migrated']
            logger.info(f"📊 Avg chunks/doc:   {avg_chunks:.1f}")
        
        logger.info("=" * 80)
        
        if dry_run:
            logger.info("⚠️  This was a DRY RUN - no changes were made")
            logger.info("   Run without --dry-run to perform actual migration")
    
    async def verify_migration(self):
        """Verify migration results"""
        logger.info("=" * 80)
        logger.info("🔍 VERIFYING MIGRATION")
        logger.info("=" * 80)
        
        await self.initialize()
        docs = await self.get_all_documents()
        
        verified = 0
        missing = 0
        
        for doc in docs:
            doc_id = doc.get('id')
            filename = doc.get('filename', 'unknown')
            
            stats = self.vector_store.get_stats(doc_id)
            if stats.get('exists') and stats.get('chunks_count', 0) > 0:
                verified += 1
                logger.info(f"✅ {filename}: {stats['chunks_count']} chunks")
            else:
                missing += 1
                logger.warning(f"❌ {filename}: NOT in Vector DB")
        
        logger.info("=" * 80)
        logger.info(f"✅ Verified:  {verified}/{len(docs)}")
        logger.info(f"❌ Missing:   {missing}/{len(docs)}")
        logger.info("=" * 80)
    
    async def cleanup(self):
        """Cleanup connections"""
        logger.info("🧹 Cleaning up...")
        await MongoDBConnection.disconnect()
        logger.info("✅ Cleanup complete")


async def main():
    """Main migration function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate documents to Vector DB')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (no changes)')
    parser.add_argument('--verify', action='store_true', help='Verify migration results')
    parser.add_argument('--batch-size', type=int, default=5, help='Batch size (default: 5)')
    args = parser.parse_args()
    
    migration = VectorDBMigration()
    
    try:
        if args.verify:
            await migration.verify_migration()
        else:
            await migration.migrate_all(
                batch_size=args.batch_size,
                dry_run=args.dry_run
            )
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
    finally:
        await migration.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

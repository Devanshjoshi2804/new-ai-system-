"""Data Collector for ML Model Training"""
import logging
import json
from typing import List, Dict, Optional
import random
from motor.motor_asyncio import AsyncIOMotorClient
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

class DataCollector:
    """Collect training data from MongoDB"""
    
    def __init__(self):
        self.client = None
        self.db = None
        
    async def connect(self):
        if not self.client:
            self.client = AsyncIOMotorClient(settings.mongodb_url)
            self.db = self.client[settings.mongodb_database]
            logger.info("DataCollector connected")
    
    async def collect_endpoint_examples(self, limit: int = 1000) -> List[Dict]:
        await self.connect()
        examples = []
        
        try:
            cursor = self.db.test_executions.find({}).limit(limit)
            async for doc in cursor:
                if 'endpoint' in doc:
                    examples.append({
                        'url': doc['endpoint'],
                        'method': doc.get('method', 'GET'),
                        'label': self._infer_label(doc['endpoint'], doc.get('method', 'GET'))
                    })
        except Exception as e:
            logger.error(f"Error: {e}")
        
        return examples
    
    def _infer_label(self, url: str, method: str) -> str:
        url_lower = url.lower()
        if 'auth' in url_lower: return 'AUTH'
        elif 'health' in url_lower: return 'HEALTH'
        elif method == 'POST': return 'CREATE'
        elif method == 'GET': return 'READ'
        elif method in ['PUT', 'PATCH']: return 'UPDATE'
        elif method == 'DELETE': return 'DELETE'
        return 'READ'
    
    async def export_training_data(self, output_path: str):
        examples = await self.collect_endpoint_examples()
        random.shuffle(examples)
        
        train_size = int(len(examples) * 0.7)
        val_size = int(len(examples) * 0.15)
        
        data = {
            'train': examples[:train_size],
            'val': examples[train_size:train_size + val_size],
            'test': examples[train_size + val_size:]
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Exported {len(examples)} examples")
        return data

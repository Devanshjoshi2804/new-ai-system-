"""
Learning Loop

Continuous improvement system that learns from test execution results.

Features:
- Stores successful test patterns in Flow DB (ChromaDB)
- Extracts features from API requests/responses
- Prepares training data for ML models
- Tracks learning metrics and ROI
- Triggers model retraining when thresholds met
"""

import logging
import json
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)


class LearningLoop:
    """
    Continuous learning system for API integration patterns

    Stores successful test executions and extracts patterns for
    future ML model training and improvement.
    """

    def __init__(
        self,
        flow_db_path: str = "./data/flow_chroma_db",
        enable_learning: bool = True,
        min_patterns_for_retrain: int = 100
    ):
        """
        Initialize learning loop

        Args:
            flow_db_path: Path to Flow DB (ChromaDB)
            enable_learning: Whether learning is enabled
            min_patterns_for_retrain: Minimum patterns before triggering retrain
        """
        self.flow_db_path = Path(flow_db_path)
        self.enable_learning = enable_learning
        self.min_patterns_for_retrain = min_patterns_for_retrain

        # ChromaDB client (lazy initialized)
        self.chroma_client = None
        self.collection = None

        # Learning metrics
        self.metrics = {
            'total_patterns_stored': 0,
            'patterns_by_category': {},
            'successful_predictions': 0,
            'failed_predictions': 0,
            'retraining_triggered': 0,
            'last_retrain_time': None
        }

        logger.info(f"[LEARNING] Initialized learning loop: db_path={flow_db_path}")

    async def initialize(self):
        """Initialize ChromaDB connection"""
        if not self.enable_learning:
            logger.info("[LEARNING] Learning disabled")
            return

        try:
            # Lazy import ChromaDB
            import chromadb
            from chromadb.config import Settings

            # Ensure directory exists
            self.flow_db_path.mkdir(parents=True, exist_ok=True)

            # Initialize client
            self.chroma_client = chromadb.PersistentClient(
                path=str(self.flow_db_path),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # Get or create collection
            self.collection = self.chroma_client.get_or_create_collection(
                name="api_patterns",
                metadata={"description": "Learned API integration patterns"}
            )

            logger.info(f"[LEARNING] ChromaDB initialized: {self.collection.count()} patterns stored")

        except Exception as e:
            logger.error(f"[LEARNING] Failed to initialize ChromaDB: {e}")
            self.enable_learning = False

    async def process_results(
        self,
        endpoints: List[Any],
        classifications: Dict[str, Dict[str, Any]],
        payloads: Dict[str, Dict[str, Any]],
        test_results: List[Any]
    ) -> int:
        """
        Process test results and extract learning patterns

        Args:
            endpoints: List of endpoint info
            classifications: Classification results
            payloads: Generated payloads
            test_results: Test execution results

        Returns:
            Number of patterns learned
        """
        if not self.enable_learning:
            logger.debug("[LEARNING] Learning disabled, skipping")
            return 0

        # Ensure initialized
        if not self.collection:
            await self.initialize()
            if not self.collection:
                return 0

        logger.info("[LEARNING] Processing results for learning...")

        patterns_learned = 0

        try:
            # Process each successful test
            for test_result in test_results:
                # Only learn from successful tests
                if test_result.status.value != 'passed':
                    continue

                # Find corresponding endpoint
                endpoint = next(
                    (ep for ep in endpoints if ep.id == test_result.endpoint_id),
                    None
                )

                if not endpoint:
                    continue

                # Extract pattern
                pattern = await self._extract_pattern(
                    endpoint=endpoint,
                    classification=classifications.get(test_result.endpoint_id, {}),
                    payload=payloads.get(test_result.endpoint_id, {}),
                    test_result=test_result
                )

                if pattern:
                    # Store pattern
                    await self._store_pattern(pattern)
                    patterns_learned += 1

            # Update metrics
            self.metrics['total_patterns_stored'] += patterns_learned

            # Check if retraining should be triggered
            if patterns_learned > 0:
                await self._check_retrain_threshold()

            logger.info(f"[LEARNING] Learned {patterns_learned} new patterns")

            return patterns_learned

        except Exception as e:
            logger.error(f"[LEARNING] Error processing results: {e}")
            return 0

    async def _extract_pattern(
        self,
        endpoint: Any,
        classification: Dict[str, Any],
        payload: Dict[str, Any],
        test_result: Any
    ) -> Optional[Dict[str, Any]]:
        """
        Extract learning pattern from successful test

        Args:
            endpoint: Endpoint info
            classification: Classification result
            payload: Request payload
            test_result: Test result

        Returns:
            Extracted pattern or None
        """
        try:
            # Build pattern document
            pattern = {
                'endpoint_url': endpoint.url,
                'method': endpoint.method,
                'category': classification.get('category', 'unknown'),
                'request': {
                    'url': endpoint.url,
                    'method': endpoint.method,
                    'payload': payload,
                    'headers': dict(endpoint.headers)
                },
                'response': test_result.response if hasattr(test_result, 'response') else {},
                'latency_ms': test_result.latency_ms if hasattr(test_result, 'latency_ms') else 0,
                'timestamp': datetime.utcnow().isoformat(),
                'metadata': {
                    'endpoint_id': endpoint.id,
                    'confidence': classification.get('confidence', 0.0),
                    'retry_count': test_result.retry_count if hasattr(test_result, 'retry_count') else 0
                }
            }

            return pattern

        except Exception as e:
            logger.warning(f"[LEARNING] Failed to extract pattern: {e}")
            return None

    async def _store_pattern(self, pattern: Dict[str, Any]):
        """
        Store pattern in Flow DB

        Args:
            pattern: Pattern to store
        """
        try:
            # Generate unique ID
            pattern_id = self._generate_pattern_id(pattern)

            # Create document text for embedding
            doc_text = self._pattern_to_text(pattern)

            # Store in ChromaDB
            self.collection.add(
                documents=[doc_text],
                metadatas=[pattern],
                ids=[pattern_id]
            )

            # Update category metrics
            category = pattern.get('category', 'unknown')
            if category not in self.metrics['patterns_by_category']:
                self.metrics['patterns_by_category'][category] = 0
            self.metrics['patterns_by_category'][category] += 1

            logger.debug(f"[LEARNING] Stored pattern: {pattern_id}")

        except Exception as e:
            logger.error(f"[LEARNING] Failed to store pattern: {e}")

    def _generate_pattern_id(self, pattern: Dict[str, Any]) -> str:
        """Generate unique ID for pattern"""
        # Create hash from key fields
        key_str = f"{pattern['method']}:{pattern['endpoint_url']}:{pattern['timestamp']}"
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]

    def _pattern_to_text(self, pattern: Dict[str, Any]) -> str:
        """Convert pattern to text for embedding"""
        parts = [
            f"Method: {pattern['method']}",
            f"URL: {pattern['endpoint_url']}",
            f"Category: {pattern['category']}",
            f"Payload: {json.dumps(pattern['request']['payload'])}",
            f"Response: {json.dumps(pattern['response'])}",
        ]
        return "\n".join(parts)

    async def _check_retrain_threshold(self):
        """Check if enough patterns collected to trigger retraining"""
        try:
            total_patterns = self.collection.count()

            # Check if last retrain time exists
            last_retrain = self.metrics.get('last_retrain_time')

            if last_retrain:
                # Calculate patterns since last retrain
                # (In production, would track this more accurately)
                patterns_since_retrain = total_patterns % self.min_patterns_for_retrain
            else:
                patterns_since_retrain = total_patterns

            if patterns_since_retrain >= self.min_patterns_for_retrain:
                logger.info(
                    f"[LEARNING] Retrain threshold met: "
                    f"{patterns_since_retrain} >= {self.min_patterns_for_retrain}"
                )
                await self._trigger_retrain()

        except Exception as e:
            logger.error(f"[LEARNING] Error checking retrain threshold: {e}")

    async def _trigger_retrain(self):
        """Trigger ML model retraining"""
        try:
            logger.info("[LEARNING] Triggering model retraining...")

            # In production, this would:
            # 1. Export patterns to training format
            # 2. Call training pipeline
            # 3. Evaluate new models
            # 4. Update model registry

            # For now, just log and update metrics
            self.metrics['retraining_triggered'] += 1
            self.metrics['last_retrain_time'] = datetime.utcnow().isoformat()

            logger.info("[LEARNING] Retraining triggered (placeholder)")

        except Exception as e:
            logger.error(f"[LEARNING] Failed to trigger retrain: {e}")

    async def query_similar_patterns(
        self,
        endpoint_url: str,
        method: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Query similar patterns from Flow DB

        Args:
            endpoint_url: Endpoint URL
            method: HTTP method
            top_k: Number of similar patterns to return

        Returns:
            List of similar patterns
        """
        if not self.enable_learning or not self.collection:
            return []

        try:
            # Create query text
            query_text = f"Method: {method}\nURL: {endpoint_url}"

            # Query ChromaDB
            results = self.collection.query(
                query_texts=[query_text],
                n_results=top_k
            )

            # Extract patterns from results
            patterns = []
            if results and 'metadatas' in results and results['metadatas']:
                for metadata in results['metadatas'][0]:
                    patterns.append(metadata)

            logger.debug(f"[LEARNING] Found {len(patterns)} similar patterns")

            return patterns

        except Exception as e:
            logger.error(f"[LEARNING] Error querying patterns: {e}")
            return []

    async def get_training_data(
        self,
        category: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get training data for ML models

        Args:
            category: Optional category filter
            limit: Optional limit on number of patterns

        Returns:
            List of training patterns
        """
        if not self.enable_learning or not self.collection:
            return []

        try:
            # Get all patterns (or filtered by category)
            if category:
                results = self.collection.get(
                    where={"category": category},
                    limit=limit
                )
            else:
                results = self.collection.get(limit=limit)

            # Extract metadata
            patterns = []
            if results and 'metadatas' in results:
                patterns = results['metadatas']

            logger.info(f"[LEARNING] Retrieved {len(patterns)} training patterns")

            return patterns

        except Exception as e:
            logger.error(f"[LEARNING] Error getting training data: {e}")
            return []

    async def export_training_data(
        self,
        output_path: str,
        format: str = 'jsonl'
    ) -> bool:
        """
        Export training data to file

        Args:
            output_path: Output file path
            format: Output format ('jsonl' or 'json')

        Returns:
            True if successful
        """
        try:
            patterns = await self.get_training_data()

            if not patterns:
                logger.warning("[LEARNING] No patterns to export")
                return False

            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            if format == 'jsonl':
                # Write as JSONL (one JSON per line)
                with open(output_file, 'w') as f:
                    for pattern in patterns:
                        f.write(json.dumps(pattern) + '\n')
            else:
                # Write as JSON array
                with open(output_file, 'w') as f:
                    json.dump(patterns, f, indent=2)

            logger.info(f"[LEARNING] Exported {len(patterns)} patterns to {output_path}")
            return True

        except Exception as e:
            logger.error(f"[LEARNING] Error exporting training data: {e}")
            return False

    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get learning metrics

        Returns:
            Dictionary with metrics
        """
        metrics = dict(self.metrics)

        # Add current pattern count
        if self.collection:
            try:
                metrics['current_pattern_count'] = self.collection.count()
            except:
                metrics['current_pattern_count'] = 0

        # Calculate learning rate
        if metrics['successful_predictions'] + metrics['failed_predictions'] > 0:
            total = metrics['successful_predictions'] + metrics['failed_predictions']
            metrics['learning_success_rate'] = metrics['successful_predictions'] / total
        else:
            metrics['learning_success_rate'] = 0.0

        return metrics

    async def reset(self):
        """Reset learning loop (for testing)"""
        try:
            if self.collection:
                self.chroma_client.delete_collection("api_patterns")
                self.collection = self.chroma_client.create_collection(
                    name="api_patterns",
                    metadata={"description": "Learned API integration patterns"}
                )

            # Reset metrics
            self.metrics = {
                'total_patterns_stored': 0,
                'patterns_by_category': {},
                'successful_predictions': 0,
                'failed_predictions': 0,
                'retraining_triggered': 0,
                'last_retrain_time': None
            }

            logger.info("[LEARNING] Learning loop reset")

        except Exception as e:
            logger.error(f"[LEARNING] Error resetting: {e}")

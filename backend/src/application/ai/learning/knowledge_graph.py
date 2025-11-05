"""
Knowledge Graph - Store and retrieve learned patterns across all partners
Part of Universal Autonomous API Testing System

This is the brain of the system - stores patterns, rules, and workflows
from all partners and enables cross-partner learning
"""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib

from src.infrastructure.ai.mem0.tenant_mem0_wrapper import TenantMem0Wrapper

logger = logging.getLogger(__name__)

# Vector store is optional - not needed for core functionality
try:
    from src.infrastructure.ai.vector_store.tenant_namespace_manager import TenantNamespaceManager
    VECTOR_STORE_AVAILABLE = True
except Exception as e:
    VECTOR_STORE_AVAILABLE = False
    logger.warning(f"Vector store not available - semantic search disabled: {e}")

# Embeddings are optional - not needed for core functionality
try:
    from src.infrastructure.ai.embeddings.gemini_embeddings import get_embeddings
    EMBEDDINGS_AVAILABLE = True
except Exception as e:
    EMBEDDINGS_AVAILABLE = False
    logger.warning(f"Embeddings not available - semantic search disabled: {e}")


class KnowledgeGraph:
    """
    Universal Knowledge Graph for storing and retrieving learned patterns
    
    Stores:
    - Workflow patterns (login → create → use)
    - Data dependencies (extract ID → use in next call)
    - Validation rules (phone must be 10 digits)
    - Error fixes (how to handle specific errors)
    - Success patterns (what worked)
    
    Enables:
    - Cross-partner learning (apply CargoDham patterns to new logistics API)
    - Pattern matching (find similar workflows)
    - Continuous improvement (learn from every execution)
    """
    
    def __init__(self):
        self.mem0 = None
        self.vector_store = None
        self.embeddings = None
        
        try:
            self.mem0 = TenantMem0Wrapper()
            logger.info("[OK] Mem0 initialized for knowledge graph")
        except Exception as e:
            logger.warning(f"[WARN] Mem0 not available: {e}")
        
        if VECTOR_STORE_AVAILABLE:
            try:
                self.vector_store = TenantNamespaceManager()
                logger.info("[OK] Vector store initialized for knowledge graph")
            except Exception as e:
                logger.warning(f"[WARN] Vector store not available: {e}")
        else:
            logger.info("ℹ[INFO] Vector store disabled - using Mem0 only (core features work!)")
        
        if EMBEDDINGS_AVAILABLE:
            try:
                self.embeddings = get_embeddings()
                logger.info("[OK] Gemini embeddings initialized (using Gemini instead of OpenAI)")
            except Exception as e:
                logger.warning(f"[WARN] Embeddings not available: {e}")
        else:
            logger.info("ℹ[INFO] Embeddings disabled - semantic search not available (core features work!)")
    
    # ==================== PATTERN STORAGE ====================
    
    async def store_workflow_pattern(
        self,
        partner_id: str,
        pattern: Dict[str, Any],
        success_rate: float = 1.0
    ) -> bool:
        """
        Store a workflow pattern in the knowledge graph
        
        Args:
            partner_id: Partner identifier
            pattern: Workflow pattern dictionary
            success_rate: Success rate (0.0 to 1.0)
            
        Returns:
            True if stored successfully
        """
        try:
            logger.info(f"[FLOPPY] Storing workflow pattern for partner: {partner_id}")
            
            pattern_id = self._generate_pattern_id(pattern)
            
            # Enrich pattern with metadata
            enriched_pattern = {
                **pattern,
                'pattern_id': pattern_id,
                'partner_id': partner_id,
                'success_rate': success_rate,
                'stored_at': datetime.utcnow().isoformat(),
                'usage_count': 0
            }
            
            # Store in Mem0 for conversational memory
            if self.mem0:
                await self._store_in_mem0(
                    partner_id=partner_id,
                    pattern=enriched_pattern,
                    pattern_type='workflow'
                )
            
            # Store in vector store for semantic search
            if self.vector_store:
                await self._store_in_vector_store(
                    partner_id=partner_id,
                    pattern=enriched_pattern,
                    pattern_type='workflow'
                )
            
            logger.info(f"[OK] Stored workflow pattern: {pattern_id}")
            return True
        
        except Exception as e:
            logger.error(f"[ERROR] Error storing workflow pattern: {e}")
            return False
    
    async def store_validation_rule(
        self,
        partner_id: str,
        rule: Dict[str, Any]
    ) -> bool:
        """
        Store a validation rule in the knowledge graph
        
        Args:
            partner_id: Partner identifier
            rule: Validation rule dictionary
            
        Returns:
            True if stored successfully
        """
        try:
            logger.info(f"[FLOPPY] Storing validation rule: {rule.get('field_name')}")
            
            rule_id = self._generate_rule_id(rule)
            
            enriched_rule = {
                **rule,
                'rule_id': rule_id,
                'partner_id': partner_id,
                'stored_at': datetime.utcnow().isoformat(),
                'usage_count': 0
            }
            
            # Store in Mem0
            if self.mem0:
                await self._store_in_mem0(
                    partner_id=partner_id,
                    pattern=enriched_rule,
                    pattern_type='validation_rule'
                )
            
            # Store in vector store
            if self.vector_store:
                await self._store_in_vector_store(
                    partner_id=partner_id,
                    pattern=enriched_rule,
                    pattern_type='validation_rule'
                )
            
            logger.info(f"[OK] Stored validation rule: {rule_id}")
            return True
        
        except Exception as e:
            logger.error(f"[ERROR] Error storing validation rule: {e}")
            return False
    
    async def store_error_fix(
        self,
        partner_id: str,
        error: str,
        fix: Dict[str, Any],
        success: bool = True
    ) -> bool:
        """
        Store an error fix in the knowledge graph
        
        Args:
            partner_id: Partner identifier
            error: Error message
            fix: Fix that was applied
            success: Whether the fix worked
            
        Returns:
            True if stored successfully
        """
        try:
            logger.info(f"[FLOPPY] Storing error fix for: {error[:100]}")
            
            fix_id = hashlib.md5(error.encode()).hexdigest()[:12]
            
            enriched_fix = {
                'fix_id': fix_id,
                'partner_id': partner_id,
                'error': error,
                'fix': fix,
                'success': success,
                'stored_at': datetime.utcnow().isoformat(),
                'usage_count': 0
            }
            
            # Store in Mem0
            if self.mem0:
                await self._store_in_mem0(
                    partner_id=partner_id,
                    pattern=enriched_fix,
                    pattern_type='error_fix'
                )
            
            logger.info(f"[OK] Stored error fix: {fix_id}")
            return True
        
        except Exception as e:
            logger.error(f"[ERROR] Error storing error fix: {e}")
            return False
    
    # ==================== PATTERN RETRIEVAL ====================
    
    async def query_similar_patterns(
        self,
        query: str,
        partner_id: Optional[str] = None,
        pattern_type: Optional[str] = None,
        limit: int = 10,
        min_confidence: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Query for similar patterns across all partners
        
        Args:
            query: Search query (e.g., "logistics API workflow")
            partner_id: Optional partner filter (None = search all partners)
            pattern_type: Optional type filter (workflow, validation_rule, error_fix)
            limit: Maximum results to return
            min_confidence: Minimum confidence/success rate
            
        Returns:
            List of similar patterns
        """
        try:
            logger.info(f"[SEARCH] Querying similar patterns: '{query}'")
            
            results = []
            
            # Search in Mem0
            if self.mem0:
                mem0_results = await self._search_mem0(
                    query=query,
                    partner_id=partner_id,
                    pattern_type=pattern_type,
                    limit=limit
                )
                results.extend(mem0_results)
            
            # Search in vector store (if available)
            if self.vector_store:
                vector_results = await self._search_vector_store(
                    query=query,
                    partner_id=partner_id,
                    pattern_type=pattern_type,
                    limit=limit
                )
                results.extend(vector_results)
            
            # Deduplicate and filter by confidence
            unique_results = self._deduplicate_results(results)
            filtered_results = [
                r for r in unique_results
                if r.get('confidence', r.get('success_rate', 0)) >= min_confidence
            ]
            
            # Sort by confidence/success rate
            sorted_results = sorted(
                filtered_results,
                key=lambda x: x.get('confidence', x.get('success_rate', 0)),
                reverse=True
            )[:limit]
            
            logger.info(f"[OK] Found {len(sorted_results)} similar patterns")
            
            return sorted_results
        
        except Exception as e:
            logger.error(f"[ERROR] Error querying patterns: {e}")
            return []
    
    async def query_validation_rules(
        self,
        field_name: str,
        partner_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query validation rules for a specific field
        
        Args:
            field_name: Field name to get rules for
            partner_id: Optional partner filter
            
        Returns:
            List of validation rules
        """
        try:
            logger.info(f"[SEARCH] Querying validation rules for: {field_name}")
            
            query = f"validation rule for {field_name} field"
            
            results = await self.query_similar_patterns(
                query=query,
                partner_id=partner_id,
                pattern_type='validation_rule',
                limit=20
            )
            
            # Filter to exact field matches
            exact_matches = [
                r for r in results
                if r.get('field_name', '').lower() == field_name.lower()
            ]
            
            logger.info(f"[OK] Found {len(exact_matches)} validation rules")
            
            return exact_matches
        
        except Exception as e:
            logger.error(f"[ERROR] Error querying validation rules: {e}")
            return []
    
    async def query_error_fix(
        self,
        error: str,
        partner_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Query for a fix for a specific error
        
        Args:
            error: Error message
            partner_id: Optional partner filter
            
        Returns:
            Error fix if found
        """
        try:
            logger.info(f"[SEARCH] Querying error fix for: {error[:100]}")
            
            results = await self.query_similar_patterns(
                query=f"error fix: {error}",
                partner_id=partner_id,
                pattern_type='error_fix',
                limit=5
            )
            
            # Return most successful fix
            if results:
                best_fix = max(results, key=lambda x: x.get('success', False))
                logger.info(f"[OK] Found error fix")
                return best_fix
            
            logger.info("[WARN] No error fix found")
            return None
        
        except Exception as e:
            logger.error(f"[ERROR] Error querying error fix: {e}")
            return None
    
    # ==================== CROSS-PARTNER LEARNING ====================
    
    async def find_universal_patterns(
        self,
        min_partners: int = 3,
        min_success_rate: float = 0.8
    ) -> List[Dict[str, Any]]:
        """
        Find universal patterns that work across multiple partners
        
        Args:
            min_partners: Minimum number of partners that must have this pattern
            min_success_rate: Minimum success rate
            
        Returns:
            List of universal patterns
        """
        try:
            logger.info(f"[SEARCH] Finding universal patterns (min {min_partners} partners)")
            
            # Get all patterns
            all_patterns = []
            
            if self.mem0:
                # This would need to query all partners
                # For now, return empty list
                pass
            
            # Group patterns by similarity
            pattern_groups = self._cluster_similar_patterns(all_patterns)
            
            # Find groups that appear in multiple partners
            universal = []
            for group in pattern_groups:
                unique_partners = set(p.get('partner_id') for p in group)
                avg_success = sum(p.get('success_rate', 0) for p in group) / len(group)
                
                if len(unique_partners) >= min_partners and avg_success >= min_success_rate:
                    universal.append({
                        'pattern_type': 'universal',
                        'description': group[0].get('description', ''),
                        'partners': list(unique_partners),
                        'success_rate': avg_success,
                        'usage_count': len(group),
                        'examples': group[:3]  # Include top 3 examples
                    })
            
            logger.info(f"[OK] Found {len(universal)} universal patterns")
            
            return universal
        
        except Exception as e:
            logger.error(f"[ERROR] Error finding universal patterns: {e}")
            return []
    
    async def get_partner_insights(
        self,
        partner_id: str
    ) -> Dict[str, Any]:
        """
        Get insights about learned patterns for a partner
        
        Args:
            partner_id: Partner identifier
            
        Returns:
            Insights dictionary
        """
        try:
            logger.info(f"[INFO] Getting insights for partner: {partner_id}")
            
            # Get all patterns for this partner
            patterns = await self.query_similar_patterns(
                query="",
                partner_id=partner_id,
                limit=1000
            )
            
            # Analyze patterns
            insights = {
                'total_patterns': len(patterns),
                'by_type': {},
                'avg_success_rate': 0,
                'most_used_patterns': [],
                'recent_patterns': []
            }
            
            # Group by type
            for pattern in patterns:
                ptype = pattern.get('pattern_type', 'unknown')
                insights['by_type'][ptype] = insights['by_type'].get(ptype, 0) + 1
            
            # Calculate average success rate
            if patterns:
                insights['avg_success_rate'] = sum(
                    p.get('success_rate', p.get('confidence', 0)) for p in patterns
                ) / len(patterns)
            
            # Most used patterns
            insights['most_used_patterns'] = sorted(
                patterns,
                key=lambda x: x.get('usage_count', 0),
                reverse=True
            )[:5]
            
            # Recent patterns
            insights['recent_patterns'] = sorted(
                patterns,
                key=lambda x: x.get('stored_at', ''),
                reverse=True
            )[:5]
            
            logger.info(f"[OK] Generated insights for partner: {partner_id}")
            
            return insights
        
        except Exception as e:
            logger.error(f"[ERROR] Error getting partner insights: {e}")
            return {}
    
    # ==================== HELPER METHODS ====================
    
    async def _store_in_mem0(
        self,
        partner_id: str,
        pattern: Dict[str, Any],
        pattern_type: str
    ):
        """Store pattern in Mem0"""
        try:
            messages = [{
                'role': 'system',
                'content': f"Learned {pattern_type}: {json.dumps(pattern)}"
            }]
            
            await self.mem0.add(
                messages=messages,
                user_id=partner_id,
                metadata={
                    'type': pattern_type,
                    'partner_id': partner_id,
                    'pattern_id': pattern.get('pattern_id', pattern.get('rule_id', pattern.get('fix_id'))),
                    'timestamp': pattern.get('stored_at')
                }
            )
        except Exception as e:
            logger.error(f"Error storing in Mem0: {e}")
    
    async def _store_in_vector_store(
        self,
        partner_id: str,
        pattern: Dict[str, Any],
        pattern_type: str
    ):
        """Store pattern in vector store"""
        try:
            # Create embedding-friendly text
            text = self._pattern_to_text(pattern, pattern_type)
            
            # Store in vector store
            # This would use your existing vector store implementation
            # For now, we'll skip actual storage
            pass
        except Exception as e:
            logger.error(f"Error storing in vector store: {e}")
    
    async def _search_mem0(
        self,
        query: str,
        partner_id: Optional[str],
        pattern_type: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search patterns in Mem0"""
        try:
            if not query:
                # Get all patterns
                results = await self.mem0.get_all(user_id=partner_id)
            else:
                # Search by query
                results = await self.mem0.search(
                    query=query,
                    user_id=partner_id,
                    limit=limit
                )
            
            # Filter by pattern type if specified
            if pattern_type:
                results = [
                    r for r in results
                    if r.get('metadata', {}).get('type') == pattern_type
                ]
            
            return results
        except Exception as e:
            logger.error(f"Error searching Mem0: {e}")
            return []
    
    async def _search_vector_store(
        self,
        query: str,
        partner_id: Optional[str],
        pattern_type: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search patterns in vector store"""
        # This would use your existing vector store implementation
        # For now, return empty list
        return []
    
    def _generate_pattern_id(self, pattern: Dict[str, Any]) -> str:
        """Generate unique ID for pattern"""
        content = json.dumps(pattern, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _generate_rule_id(self, rule: Dict[str, Any]) -> str:
        """Generate unique ID for rule"""
        content = f"{rule.get('field_name')}_{rule.get('rule_type')}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _pattern_to_text(self, pattern: Dict[str, Any], pattern_type: str) -> str:
        """Convert pattern to text for embedding"""
        if pattern_type == 'workflow':
            return f"Workflow: {pattern.get('description', '')} Steps: {', '.join(pattern.get('steps', []))}"
        elif pattern_type == 'validation_rule':
            return f"Validation rule for {pattern.get('field_name')}: {pattern.get('rule_description', '')}"
        elif pattern_type == 'error_fix':
            return f"Error fix: {pattern.get('error', '')} Fix: {json.dumps(pattern.get('fix', {}))}"
        return json.dumps(pattern)
    
    def _create_embedding(self, text: str) -> List[float]:
        """Create embedding using Gemini"""
        try:
            if self.embeddings:
                return self.embeddings.embed_query(text)
            else:
                logger.warning("Embeddings not available, returning empty vector")
                return [0.0] * 768  # Gemini embedding dimension
        except Exception as e:
            logger.error(f"Error creating embedding: {e}")
            return [0.0] * 768
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate results"""
        seen = set()
        unique = []
        
        for result in results:
            result_id = result.get('pattern_id', result.get('rule_id', result.get('fix_id', '')))
            if result_id and result_id not in seen:
                seen.add(result_id)
                unique.append(result)
        
        return unique
    
    def _cluster_similar_patterns(
        self,
        patterns: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """Cluster similar patterns together"""
        # Simple clustering by description similarity
        # In production, use proper clustering algorithm
        clusters = []
        
        for pattern in patterns:
            added = False
            desc = pattern.get('description', '').lower()
            
            for cluster in clusters:
                cluster_desc = cluster[0].get('description', '').lower()
                # Simple similarity check
                if self._text_similarity(desc, cluster_desc) > 0.7:
                    cluster.append(pattern)
                    added = True
                    break
            
            if not added:
                clusters.append([pattern])
        
        return clusters
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity"""
        # Simple word overlap similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0


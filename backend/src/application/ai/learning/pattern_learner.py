"""
Pattern Learner - Learn from successful API executions
"""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.infrastructure.ai.mem0.tenant_mem0_wrapper import TenantMem0Wrapper

logger = logging.getLogger(__name__)


class PatternLearner:
    """Learn from successful API executions and store patterns"""
    
    def __init__(self):
        self.mem0 = None
        try:
            self.mem0 = TenantMem0Wrapper()
            logger.info("[OK] Mem0 initialized for pattern learning")
        except Exception as e:
            logger.warning(f"[WARN] Mem0 not available: {e}")
    
    async def store_successful_pattern(
        self,
        user_intent: str,
        execution_plan: List[Dict[str, Any]],
        api_responses: List[Dict[str, Any]],
        partner_id: str,
        collected_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store successful execution pattern in Mem0
        
        Args:
            user_intent: User's original command
            execution_plan: The execution plan that succeeded
            api_responses: API responses from execution
            partner_id: Partner identifier
            collected_data: Data collected during execution
            
        Returns:
            True if stored successfully
        """
        try:
            if not self.mem0:
                logger.warning("[WARN] Mem0 not available, skipping pattern storage")
                return False
            
            logger.info(f"[FLOPPY] Storing successful pattern for: '{user_intent}'")
            
            # Create pattern summary
            pattern = {
                'intent': user_intent,
                'execution_plan': execution_plan,
                'success': True,
                'timestamp': datetime.utcnow().isoformat(),
                'partner_id': partner_id,
                'steps_count': len(execution_plan),
                'api_calls_count': len(api_responses),
                'collected_data_keys': list(collected_data.keys()) if collected_data else []
            }
            
            # Store in Mem0
            messages = [{
                'role': 'user',
                'content': f"Successful API execution pattern: {user_intent}"
            }, {
                'role': 'assistant',
                'content': f"Executed successfully with {len(execution_plan)} steps. Pattern: {json.dumps(pattern)}"
            }]
            
            await self.mem0.add(
                messages=messages,
                user_id=partner_id,
                metadata={
                    'type': 'successful_pattern',
                    'partner_id': partner_id,
                    'intent': user_intent,
                    'timestamp': pattern['timestamp']
                }
            )
            
            logger.info("[OK] Pattern stored successfully")
            return True
        
        except Exception as e:
            logger.error(f"[ERROR] Error storing pattern: {e}")
            return False
    
    async def find_similar_patterns(
        self,
        user_intent: str,
        partner_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find similar successful patterns from history
        
        Args:
            user_intent: User's command to find similar patterns for
            partner_id: Partner identifier
            limit: Maximum number of patterns to return
            
        Returns:
            List of similar patterns
        """
        try:
            if not self.mem0:
                logger.warning("[WARN] Mem0 not available, returning empty patterns")
                return []
            
            logger.info(f"[SEARCH] Finding similar patterns for: '{user_intent}'")
            
            # Search in Mem0
            similar = await self.mem0.search(
                query=user_intent,
                user_id=partner_id,
                limit=limit
            )
            
            logger.info(f"[OK] Found {len(similar)} similar patterns")
            
            return similar
        
        except Exception as e:
            logger.error(f"[ERROR] Error finding patterns: {e}")
            return []
    
    async def store_failure_pattern(
        self,
        user_intent: str,
        execution_plan: List[Dict[str, Any]],
        error: str,
        partner_id: str
    ) -> bool:
        """
        Store failed execution pattern to learn from failures
        
        Args:
            user_intent: User's original command
            execution_plan: The execution plan that failed
            error: Error message
            partner_id: Partner identifier
            
        Returns:
            True if stored successfully
        """
        try:
            if not self.mem0:
                return False
            
            logger.info(f"[FLOPPY] Storing failure pattern for: '{user_intent}'")
            
            pattern = {
                'intent': user_intent,
                'execution_plan': execution_plan,
                'success': False,
                'error': error,
                'timestamp': datetime.utcnow().isoformat(),
                'partner_id': partner_id
            }
            
            messages = [{
                'role': 'user',
                'content': f"Failed API execution: {user_intent}"
            }, {
                'role': 'assistant',
                'content': f"Failed with error: {error}. Pattern: {json.dumps(pattern)}"
            }]
            
            await self.mem0.add(
                messages=messages,
                user_id=partner_id,
                metadata={
                    'type': 'failure_pattern',
                    'partner_id': partner_id,
                    'intent': user_intent,
                    'error': error,
                    'timestamp': pattern['timestamp']
                }
            )
            
            logger.info("[OK] Failure pattern stored")
            return True
        
        except Exception as e:
            logger.error(f"[ERROR] Error storing failure pattern: {e}")
            return False
    
    async def get_success_rate(
        self,
        partner_id: str,
        intent_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get success rate statistics
        
        Args:
            partner_id: Partner identifier
            intent_type: Optional intent type to filter by
            
        Returns:
            Success rate statistics
        """
        try:
            if not self.mem0:
                return {'success_rate': 0, 'total': 0, 'successful': 0, 'failed': 0}
            
            logger.info(f"[INFO] Getting success rate for partner: {partner_id}")
            
            # Get all patterns
            all_patterns = await self.mem0.get_all(user_id=partner_id)
            
            # Filter and count
            successful = 0
            failed = 0
            
            for pattern in all_patterns:
                metadata = pattern.get('metadata', {})
                if intent_type and metadata.get('intent') != intent_type:
                    continue
                
                if metadata.get('type') == 'successful_pattern':
                    successful += 1
                elif metadata.get('type') == 'failure_pattern':
                    failed += 1
            
            total = successful + failed
            success_rate = (successful / total * 100) if total > 0 else 0
            
            logger.info(f"[OK] Success rate: {success_rate:.1f}% ({successful}/{total})")
            
            return {
                'success_rate': success_rate,
                'total': total,
                'successful': successful,
                'failed': failed
            }
        
        except Exception as e:
            logger.error(f"[ERROR] Error getting success rate: {e}")
            return {'success_rate': 0, 'total': 0, 'successful': 0, 'failed': 0}
    
    async def get_learning_insights(
        self,
        partner_id: str
    ) -> Dict[str, Any]:
        """
        Get insights from learned patterns
        
        Args:
            partner_id: Partner identifier
            
        Returns:
            Learning insights
        """
        try:
            if not self.mem0:
                return {'insights': [], 'recommendations': []}
            
            logger.info(f"[IDEA] Getting learning insights for partner: {partner_id}")
            
            # Get all patterns
            all_patterns = await self.mem0.get_all(user_id=partner_id)
            
            # Analyze patterns
            insights = []
            recommendations = []
            
            # Count by intent type
            intent_counts = {}
            for pattern in all_patterns:
                metadata = pattern.get('metadata', {})
                intent = metadata.get('intent', 'unknown')
                intent_counts[intent] = intent_counts.get(intent, 0) + 1
            
            # Most common intents
            if intent_counts:
                most_common = max(intent_counts.items(), key=lambda x: x[1])
                insights.append({
                    'type': 'most_common_intent',
                    'insight': f"Most common command: '{most_common[0]}' ({most_common[1]} times)"
                })
            
            # Success patterns
            successful_patterns = [p for p in all_patterns if p.get('metadata', {}).get('type') == 'successful_pattern']
            if successful_patterns:
                insights.append({
                    'type': 'success_count',
                    'insight': f"{len(successful_patterns)} successful executions learned"
                })
            
            # Failure patterns
            failed_patterns = [p for p in all_patterns if p.get('metadata', {}).get('type') == 'failure_pattern']
            if failed_patterns:
                insights.append({
                    'type': 'failure_count',
                    'insight': f"{len(failed_patterns)} failures to learn from"
                })
                
                # Recommend reviewing failures
                recommendations.append({
                    'type': 'review_failures',
                    'recommendation': "Review failed patterns to improve API understanding"
                })
            
            logger.info(f"[OK] Generated {len(insights)} insights and {len(recommendations)} recommendations")
            
            return {
                'insights': insights,
                'recommendations': recommendations,
                'pattern_count': len(all_patterns),
                'success_rate': await self.get_success_rate(partner_id)
            }
        
        except Exception as e:
            logger.error(f"[ERROR] Error getting insights: {e}")
            return {'insights': [], 'recommendations': [], 'error': str(e)}


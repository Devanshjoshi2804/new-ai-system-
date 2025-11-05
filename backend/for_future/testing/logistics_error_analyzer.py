"""
Logistics-Specific Error Pattern Analyzer
Handles common logistics API failures with intelligent strategies
"""
import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class LogisticsErrorAnalyzer:
    """Recognizes and handles logistics-specific API errors"""
    
    # Logistics-specific error patterns and handling strategies
    LOGISTICS_ERROR_PATTERNS = {
        # Connectivity issues (common in warehouse WiFi)
        'connectivity': {
            'indicators': [
                'timeout', 'connection refused', 'network error',
                'connection reset', 'connection timed out',
                'unable to connect', 'no route to host'
            ],
            'strategy': 'exponential_backoff',
            'max_retries': 5,
            'initial_backoff': 2.0,
            'max_backoff': 60.0,
            'special_handling': 'warehouse_mode',
            'confidence_threshold': 0.9
        },
        
        # Data format issues (FedEx vs UPS vs DHL formats)
        'data_format': {
            'indicators': [
                'invalid address format', 'postal code format',
                'phone number format', 'invalid country code',
                'invalid format', 'format error', 'validation failed',
                'invalid field', 'field required', 'missing required field'
            ],
            'strategy': 'format_conversion',
            'ai_prompt': 'Convert data to {carrier} format based on error message',
            'vector_db_query': 'address format requirements for {carrier}',
            'confidence_threshold': 0.85
        },
        
        # Rate limiting (logistics APIs are STRICT)
        'rate_limiting': {
            'indicators': [
                'rate limit', 'too many requests', '429',
                'quota exceeded', 'throttled', 'rate exceeded',
                'api limit reached', 'request limit'
            ],
            'strategy': 'adaptive_throttling',
            'initial_backoff': 60,  # Start with 60s (not 1s!)
            'respect_retry_after': True,
            'track_per_carrier': True,
            'confidence_threshold': 0.95
        },
        
        # Service availability (pickup/delivery time restrictions)
        'service_unavailable': {
            'indicators': [
                'service not available', 'delivery not possible',
                'pickup unavailable', 'no service to destination',
                'service area', 'out of service area',
                'not serviceable', 'delivery restriction'
            ],
            'strategy': 'suggest_alternatives',
            'ai_prompt': 'Suggest alternative services or delivery times based on restrictions',
            'confidence_threshold': 0.8
        },
        
        # Weight/dimension validation
        'dimensional': {
            'indicators': [
                'weight exceeds', 'dimension invalid',
                'package too large', 'volumetric weight',
                'weight limit', 'size restriction',
                'exceeds maximum', 'dimensional weight'
            ],
            'strategy': 'recalculate',
            'ai_prompt': 'Adjust package dimensions within carrier limits',
            'confidence_threshold': 0.85
        },
        
        # Address validation failures
        'address_issues': {
            'indicators': [
                'invalid address', 'address not found',
                'undeliverable', 'po box not accepted',
                'address validation failed', 'invalid zipcode',
                'invalid postal code', 'address incomplete',
                'residential address', 'commercial address required'
            ],
            'strategy': 'address_correction',
            'vector_db_query': 'address validation rules',
            'ai_prompt': 'Correct address based on carrier requirements',
            'fallback': 'request_manual_review',
            'confidence_threshold': 0.75
        },
        
        # Customs/restricted items
        'restricted': {
            'indicators': [
                'restricted item', 'hazmat', 'customs',
                'prohibited', 'requires license', 'dangerous goods',
                'customs declaration', 'harmonized code',
                'export restrictions', 'import restrictions'
            ],
            'strategy': 'compliance_check',
            'ai_prompt': 'Check if item can be shipped with different classification',
            'escalate': True,
            'confidence_threshold': 0.9
        },
        
        # Authentication/authorization issues
        'authentication': {
            'indicators': [
                'unauthorized', '401', '403', 'forbidden',
                'invalid credentials', 'expired token',
                'authentication failed', 'invalid api key'
            ],
            'strategy': 'refresh_auth',
            'confidence_threshold': 0.95
        },
        
        # Business logic errors
        'business_logic': {
            'indicators': [
                'invalid shipment', 'booking failed',
                'cannot create shipment', 'invalid service type',
                'package details invalid', 'shipment rules'
            ],
            'strategy': 'business_logic_fix',
            'ai_prompt': 'Adjust shipment details to comply with carrier business rules',
            'confidence_threshold': 0.7
        }
    }
    
    # Carrier-specific quirks
    CARRIER_QUIRKS = {
        'fedex': {
            'address_format': 'strict',
            'requires_company_name': True,
            'phone_format': 'international',
            'rate_limit': 'very_strict',
            'common_issues': ['residential surcharge', 'address validation']
        },
        'ups': {
            'address_format': 'flexible',
            'requires_account_number': True,
            'rate_limit': 'moderate',
            'common_issues': ['service area', 'dimensional weight']
        },
        'dhl': {
            'address_format': 'international_standard',
            'requires_customs': True,
            'rate_limit': 'strict',
            'common_issues': ['customs', 'international restrictions']
        },
        'usps': {
            'address_format': 'us_postal',
            'po_box_allowed': True,
            'rate_limit': 'lenient',
            'common_issues': ['zipcode format', 'po box restrictions']
        }
    }
    
    def __init__(self, ai_provider=None, vector_store=None):
        """
        Initialize logistics error analyzer
        
        Args:
            ai_provider: AI provider for intelligent error analysis
            vector_store: Vector DB for carrier-specific documentation lookup
        """
        self.ai_provider = ai_provider
        self.vector_store = vector_store
        
        # Track error history per carrier
        self.error_history = {}
        self.carrier_patterns = {}
        
        # Rate limit tracking
        self.rate_limit_state = {}
        
        logger.info("✅ LogisticsErrorAnalyzer initialized")
    
    def analyze_error(
        self,
        error_response: Dict[str, Any],
        carrier: Optional[str] = None,
        endpoint: Optional[str] = None,
        attempt_number: int = 1
    ) -> Dict[str, Any]:
        """
        Analyze logistics API error and suggest fix
        
        Args:
            error_response: The error response from API
            carrier: Carrier name (fedex, ups, dhl, etc.)
            endpoint: API endpoint that failed
            attempt_number: Current retry attempt
            
        Returns:
            {
                'error_type': 'data_format',
                'confidence': 0.95,
                'suggested_fix': {...},
                'retry_strategy': 'format_conversion',
                'estimated_success_rate': 0.85,
                'should_retry': True,
                'backoff_seconds': 5
            }
        """
        logger.info(f"🔍 Analyzing logistics error (attempt {attempt_number})")
        
        # Extract error information
        status_code = error_response.get('status_code', 0)
        error_message = str(error_response.get('error', ''))
        response_data = error_response.get('response_data', {})
        
        # Combine all error text for pattern matching
        error_text = f"{error_message} {str(response_data)}".lower()
        
        # Match against logistics patterns
        matches = []
        for error_type, pattern_config in self.LOGISTICS_ERROR_PATTERNS.items():
            confidence = self._calculate_confidence(
                error_text,
                pattern_config['indicators']
            )
            
            if confidence >= pattern_config.get('confidence_threshold', 0.7):
                matches.append({
                    'error_type': error_type,
                    'confidence': confidence,
                    'config': pattern_config
                })
        
        # Sort by confidence
        matches.sort(key=lambda x: x['confidence'], reverse=True)
        
        if not matches:
            logger.warning("⚠️  No logistics error pattern matched")
            return self._generic_retry_strategy(status_code, error_text)
        
        # Use highest confidence match
        best_match = matches[0]
        error_type = best_match['error_type']
        config = best_match['config']
        
        logger.info(f"✅ Matched error type: {error_type} (confidence: {best_match['confidence']:.2f})")
        
        # Generate strategy based on error type
        strategy = self._generate_strategy(
            error_type=error_type,
            config=config,
            carrier=carrier,
            error_text=error_text,
            status_code=status_code,
            attempt_number=attempt_number
        )
        
        # Store in error history
        self._record_error(carrier, endpoint, error_type, strategy)
        
        return strategy
    
    def _calculate_confidence(
        self,
        error_text: str,
        indicators: List[str]
    ) -> float:
        """Calculate confidence that error matches pattern"""
        if not indicators:
            return 0.0
        
        matches = sum(1 for indicator in indicators if indicator in error_text)
        confidence = matches / len(indicators)
        
        # Boost confidence if multiple indicators match
        if matches > 1:
            confidence = min(confidence * 1.2, 1.0)
        
        return confidence
    
    def _generate_strategy(
        self,
        error_type: str,
        config: Dict[str, Any],
        carrier: Optional[str],
        error_text: str,
        status_code: int,
        attempt_number: int
    ) -> Dict[str, Any]:
        """Generate retry strategy based on error type"""
        
        strategy_name = config.get('strategy', 'generic_retry')
        
        if strategy_name == 'exponential_backoff':
            return self._exponential_backoff_strategy(config, attempt_number)
        
        elif strategy_name == 'format_conversion':
            return self._format_conversion_strategy(
                config, carrier, error_text, attempt_number
            )
        
        elif strategy_name == 'adaptive_throttling':
            return self._adaptive_throttling_strategy(
                config, carrier, attempt_number
            )
        
        elif strategy_name == 'suggest_alternatives':
            return self._suggest_alternatives_strategy(
                config, carrier, error_text
            )
        
        elif strategy_name == 'address_correction':
            return self._address_correction_strategy(
                config, error_text, attempt_number
            )
        
        elif strategy_name == 'compliance_check':
            return self._compliance_check_strategy(
                config, error_text
            )
        
        elif strategy_name == 'refresh_auth':
            return self._refresh_auth_strategy()
        
        elif strategy_name == 'business_logic_fix':
            return self._business_logic_strategy(
                config, carrier, error_text, attempt_number
            )
        
        else:
            return self._generic_retry_strategy(status_code, error_text)
    
    def _exponential_backoff_strategy(
        self,
        config: Dict[str, Any],
        attempt_number: int
    ) -> Dict[str, Any]:
        """Strategy for connectivity issues - aggressive backoff"""
        initial_backoff = config.get('initial_backoff', 2.0)
        max_backoff = config.get('max_backoff', 60.0)
        max_retries = config.get('max_retries', 5)
        
        backoff_seconds = min(
            initial_backoff * (2 ** (attempt_number - 1)),
            max_backoff
        )
        
        return {
            'error_type': 'connectivity',
            'confidence': 0.9,
            'should_retry': attempt_number < max_retries,
            'retry_strategy': 'exponential_backoff',
            'backoff_seconds': backoff_seconds,
            'estimated_success_rate': 0.7,
            'suggested_fix': {
                'action': 'wait_and_retry',
                'reason': 'Network connectivity issue - likely warehouse WiFi'
            },
            'user_message': f'Network issue detected. Retrying in {backoff_seconds:.0f}s...'
        }
    
    def _format_conversion_strategy(
        self,
        config: Dict[str, Any],
        carrier: Optional[str],
        error_text: str,
        attempt_number: int
    ) -> Dict[str, Any]:
        """Strategy for data format issues"""
        
        # Extract which field has format issue
        field_patterns = {
            'address': ['address', 'street', 'city', 'state', 'postal', 'zipcode'],
            'phone': ['phone', 'telephone', 'contact'],
            'weight': ['weight', 'kg', 'lbs'],
            'dimensions': ['length', 'width', 'height', 'dimension']
        }
        
        problem_field = None
        for field_type, patterns in field_patterns.items():
            if any(pattern in error_text for pattern in patterns):
                problem_field = field_type
                break
        
        return {
            'error_type': 'data_format',
            'confidence': 0.85,
            'should_retry': attempt_number < 3,
            'retry_strategy': 'format_conversion',
            'backoff_seconds': 2,
            'estimated_success_rate': 0.8,
            'suggested_fix': {
                'action': 'ai_format_correction',
                'field': problem_field,
                'carrier': carrier,
                'ai_prompt': config.get('ai_prompt', '').format(carrier=carrier or 'carrier'),
                'vector_db_query': config.get('vector_db_query', '').format(carrier=carrier or 'carrier')
            },
            'user_message': f'Format issue detected in {problem_field}. AI will correct...'
        }
    
    def _adaptive_throttling_strategy(
        self,
        config: Dict[str, Any],
        carrier: Optional[str],
        attempt_number: int
    ) -> Dict[str, Any]:
        """Strategy for rate limiting - respect carrier limits"""
        
        # Track rate limit state per carrier
        if carrier:
            if carrier not in self.rate_limit_state:
                self.rate_limit_state[carrier] = {
                    'hit_count': 0,
                    'last_hit': None,
                    'backoff_multiplier': 1.0
                }
            
            state = self.rate_limit_state[carrier]
            state['hit_count'] += 1
            state['last_hit'] = datetime.utcnow()
            
            # Increase backoff each time we hit rate limit
            state['backoff_multiplier'] = min(state['backoff_multiplier'] * 1.5, 5.0)
            
            backoff_seconds = config.get('initial_backoff', 60) * state['backoff_multiplier']
        else:
            backoff_seconds = config.get('initial_backoff', 60)
        
        return {
            'error_type': 'rate_limiting',
            'confidence': 0.95,
            'should_retry': attempt_number < 3,
            'retry_strategy': 'adaptive_throttling',
            'backoff_seconds': backoff_seconds,
            'estimated_success_rate': 0.9,
            'suggested_fix': {
                'action': 'respect_rate_limit',
                'carrier': carrier,
                'wait_time': backoff_seconds
            },
            'user_message': f'Rate limit reached for {carrier}. Waiting {backoff_seconds:.0f}s...'
        }
    
    def _suggest_alternatives_strategy(
        self,
        config: Dict[str, Any],
        carrier: Optional[str],
        error_text: str
    ) -> Dict[str, Any]:
        """Strategy for service unavailability"""
        return {
            'error_type': 'service_unavailable',
            'confidence': 0.8,
            'should_retry': False,  # Service not available, retrying won't help
            'retry_strategy': 'suggest_alternatives',
            'estimated_success_rate': 0.0,
            'suggested_fix': {
                'action': 'ai_suggest_alternatives',
                'carrier': carrier,
                'ai_prompt': config.get('ai_prompt', ''),
                'alternatives': [
                    'Try different service level',
                    'Try different delivery date',
                    'Try different carrier'
                ]
            },
            'user_message': 'Service not available. AI analyzing alternatives...'
        }
    
    def _address_correction_strategy(
        self,
        config: Dict[str, Any],
        error_text: str,
        attempt_number: int
    ) -> Dict[str, Any]:
        """Strategy for address validation failures"""
        return {
            'error_type': 'address_issues',
            'confidence': 0.75,
            'should_retry': attempt_number < 2,
            'retry_strategy': 'address_correction',
            'backoff_seconds': 2,
            'estimated_success_rate': 0.6,
            'suggested_fix': {
                'action': 'ai_address_correction',
                'ai_prompt': config.get('ai_prompt', ''),
                'vector_db_query': config.get('vector_db_query', ''),
                'fallback': config.get('fallback', 'manual_review')
            },
            'user_message': 'Address validation failed. AI attempting correction...'
        }
    
    def _compliance_check_strategy(
        self,
        config: Dict[str, Any],
        error_text: str
    ) -> Dict[str, Any]:
        """Strategy for restricted/compliance issues"""
        return {
            'error_type': 'restricted',
            'confidence': 0.9,
            'should_retry': False,
            'retry_strategy': 'compliance_check',
            'estimated_success_rate': 0.0,
            'suggested_fix': {
                'action': 'escalate_to_human',
                'reason': 'Restricted item or compliance issue',
                'requires_review': True,
                'ai_prompt': config.get('ai_prompt', '')
            },
            'user_message': 'Compliance issue detected. Manual review required.',
            'escalate': True
        }
    
    def _refresh_auth_strategy(self) -> Dict[str, Any]:
        """Strategy for authentication issues"""
        return {
            'error_type': 'authentication',
            'confidence': 0.95,
            'should_retry': True,
            'retry_strategy': 'refresh_auth',
            'backoff_seconds': 1,
            'estimated_success_rate': 0.95,
            'suggested_fix': {
                'action': 'refresh_authentication',
                'steps': [
                    'Get new auth token',
                    'Update headers',
                    'Retry request'
                ]
            },
            'user_message': 'Authentication expired. Refreshing token...'
        }
    
    def _business_logic_strategy(
        self,
        config: Dict[str, Any],
        carrier: Optional[str],
        error_text: str,
        attempt_number: int
    ) -> Dict[str, Any]:
        """Strategy for business logic errors"""
        return {
            'error_type': 'business_logic',
            'confidence': 0.7,
            'should_retry': attempt_number < 2,
            'retry_strategy': 'business_logic_fix',
            'backoff_seconds': 2,
            'estimated_success_rate': 0.65,
            'suggested_fix': {
                'action': 'ai_business_logic_fix',
                'carrier': carrier,
                'ai_prompt': config.get('ai_prompt', ''),
                'analyze_rules': True
            },
            'user_message': 'Business rule violation. AI analyzing requirements...'
        }
    
    def _generic_retry_strategy(
        self,
        status_code: int,
        error_text: str
    ) -> Dict[str, Any]:
        """Fallback strategy for unknown errors"""
        should_retry = status_code >= 500 or status_code == 429
        
        return {
            'error_type': 'unknown',
            'confidence': 0.5,
            'should_retry': should_retry,
            'retry_strategy': 'generic_retry',
            'backoff_seconds': 5,
            'estimated_success_rate': 0.3,
            'suggested_fix': {
                'action': 'generic_retry',
                'status_code': status_code
            },
            'user_message': f'Error {status_code}. Retrying...'
        }
    
    def _record_error(
        self,
        carrier: Optional[str],
        endpoint: Optional[str],
        error_type: str,
        strategy: Dict[str, Any]
    ):
        """Record error for pattern analysis"""
        if not carrier:
            return
        
        if carrier not in self.error_history:
            self.error_history[carrier] = []
        
        self.error_history[carrier].append({
            'timestamp': datetime.utcnow(),
            'endpoint': endpoint,
            'error_type': error_type,
            'strategy_used': strategy.get('retry_strategy'),
            'success_rate': strategy.get('estimated_success_rate')
        })
        
        # Keep only last 100 errors
        self.error_history[carrier] = self.error_history[carrier][-100:]
    
    def get_carrier_insights(self, carrier: str) -> Dict[str, Any]:
        """Get insights about carrier error patterns"""
        if carrier not in self.error_history:
            return {'message': 'No error history for this carrier'}
        
        history = self.error_history[carrier]
        
        # Count error types
        error_counts = {}
        for entry in history:
            error_type = entry['error_type']
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        return {
            'carrier': carrier,
            'total_errors': len(history),
            'error_types': error_counts,
            'most_common_error': max(error_counts, key=error_counts.get) if error_counts else None,
            'quirks': self.CARRIER_QUIRKS.get(carrier, {}),
            'rate_limit_hits': self.rate_limit_state.get(carrier, {}).get('hit_count', 0)
        }


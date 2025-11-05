"""
Performance Monitor

Real-time performance monitoring and metrics tracking system.

Features:
- Track hit rates across cache/ML/AI tiers
- Monitor latency per tier
- Calculate cost savings
- Alert on threshold violations
- Historical metrics storage
- Performance reports
"""

import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class PerformanceSnapshot:
    """Snapshot of performance metrics at a point in time"""
    timestamp: datetime

    # Request counts
    total_requests: int = 0
    cache_hits: int = 0
    ml_predictions: int = 0
    ai_predictions: int = 0
    errors: int = 0

    # Latency (milliseconds)
    avg_latency_ms: float = 0.0
    cache_latency_ms: float = 0.0
    ml_latency_ms: float = 0.0
    ai_latency_ms: float = 0.0

    # Costs (USD)
    estimated_cost: float = 0.0
    cost_saved: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'total_requests': self.total_requests,
            'cache_hits': self.cache_hits,
            'ml_predictions': self.ml_predictions,
            'ai_predictions': self.ai_predictions,
            'errors': self.errors,
            'cache_hit_rate': self.cache_hits / self.total_requests if self.total_requests > 0 else 0.0,
            'ml_usage_rate': self.ml_predictions / self.total_requests if self.total_requests > 0 else 0.0,
            'ai_usage_rate': self.ai_predictions / self.total_requests if self.total_requests > 0 else 0.0,
            'error_rate': self.errors / self.total_requests if self.total_requests > 0 else 0.0,
            'avg_latency_ms': self.avg_latency_ms,
            'cache_latency_ms': self.cache_latency_ms,
            'ml_latency_ms': self.ml_latency_ms,
            'ai_latency_ms': self.ai_latency_ms,
            'estimated_cost': self.estimated_cost,
            'cost_saved': self.cost_saved
        }


@dataclass
class Alert:
    """Performance alert"""
    severity: str  # 'info', 'warning', 'critical'
    message: str
    metric: str
    value: float
    threshold: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


class PerformanceMonitor:
    """
    Real-time performance monitoring system

    Tracks metrics across the hybrid prediction system and provides
    alerts when thresholds are violated.
    """

    def __init__(
        self,
        history_size: int = 1000,
        snapshot_interval_seconds: int = 60,
        enable_alerts: bool = True
    ):
        """
        Initialize performance monitor

        Args:
            history_size: Number of historical snapshots to keep
            snapshot_interval_seconds: Interval for periodic snapshots
            enable_alerts: Whether to enable alerting
        """
        self.history_size = history_size
        self.snapshot_interval = snapshot_interval_seconds
        self.enable_alerts = enable_alerts

        # Current metrics (accumulating)
        self.current_metrics = {
            'total_requests': 0,
            'cache_hits': 0,
            'ml_predictions': 0,
            'ai_predictions': 0,
            'errors': 0,
            'total_latency_ms': 0.0,
            'cache_latency_ms': 0.0,
            'ml_latency_ms': 0.0,
            'ai_latency_ms': 0.0,
            'estimated_cost': 0.0,
            'cost_saved': 0.0
        }

        # Historical snapshots (circular buffer)
        self.history: deque = deque(maxlen=history_size)

        # Alerts
        self.alerts: List[Alert] = []
        self.alert_thresholds = {
            'cache_hit_rate_min': 0.7,  # Alert if cache hit rate < 70%
            'error_rate_max': 0.1,  # Alert if error rate > 10%
            'avg_latency_max_ms': 500,  # Alert if avg latency > 500ms
            'ai_usage_rate_max': 0.2,  # Alert if AI usage > 20%
            'cost_per_request_max': 0.01  # Alert if cost > $0.01 per request
        }

        # Cost configuration (USD)
        self.cost_config = {
            'ai_api_cost_per_request': 0.002,  # $0.002 per AI API call
            'ml_cost_per_request': 0.0001,  # $0.0001 per ML inference (compute cost)
            'cache_cost_per_request': 0.000001  # Negligible
        }

        # Background tasks
        self._snapshot_task = None
        self._running = False

        logger.info("[PERF_MONITOR] Initialized performance monitor")

    async def start(self):
        """Start periodic snapshot collection"""
        if self._running:
            return

        self._running = True
        self._snapshot_task = asyncio.create_task(self._periodic_snapshot())

        logger.info("[PERF_MONITOR] Started periodic snapshots")

    async def stop(self):
        """Stop periodic snapshot collection"""
        self._running = False

        if self._snapshot_task:
            self._snapshot_task.cancel()
            try:
                await self._snapshot_task
            except asyncio.CancelledError:
                pass

        logger.info("[PERF_MONITOR] Stopped periodic snapshots")

    async def _periodic_snapshot(self):
        """Periodic snapshot collection"""
        while self._running:
            try:
                await asyncio.sleep(self.snapshot_interval)
                await self.create_snapshot()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[PERF_MONITOR] Snapshot error: {e}")

    async def record_prediction(
        self,
        tier: str,  # 'cache', 'ml', 'ai'
        latency_ms: float,
        success: bool = True
    ):
        """
        Record a prediction event

        Args:
            tier: Which tier served the prediction
            latency_ms: Latency in milliseconds
            success: Whether prediction was successful
        """
        self.current_metrics['total_requests'] += 1
        self.current_metrics['total_latency_ms'] += latency_ms

        if tier == 'cache':
            self.current_metrics['cache_hits'] += 1
            self.current_metrics['cache_latency_ms'] += latency_ms
            cost = self.cost_config['cache_cost_per_request']
            saved = self.cost_config['ai_api_cost_per_request'] - cost

        elif tier == 'ml':
            self.current_metrics['ml_predictions'] += 1
            self.current_metrics['ml_latency_ms'] += latency_ms
            cost = self.cost_config['ml_cost_per_request']
            saved = self.cost_config['ai_api_cost_per_request'] - cost

        elif tier == 'ai':
            self.current_metrics['ai_predictions'] += 1
            self.current_metrics['ai_latency_ms'] += latency_ms
            cost = self.cost_config['ai_api_cost_per_request']
            saved = 0.0  # No savings

        else:
            logger.warning(f"[PERF_MONITOR] Unknown tier: {tier}")
            return

        if not success:
            self.current_metrics['errors'] += 1

        self.current_metrics['estimated_cost'] += cost
        self.current_metrics['cost_saved'] += saved

        # Check alerts
        if self.enable_alerts:
            await self._check_alerts()

    async def create_snapshot(self) -> PerformanceSnapshot:
        """
        Create performance snapshot from current metrics

        Returns:
            Performance snapshot
        """
        total = self.current_metrics['total_requests']

        if total == 0:
            snapshot = PerformanceSnapshot(timestamp=datetime.utcnow())
        else:
            snapshot = PerformanceSnapshot(
                timestamp=datetime.utcnow(),
                total_requests=total,
                cache_hits=self.current_metrics['cache_hits'],
                ml_predictions=self.current_metrics['ml_predictions'],
                ai_predictions=self.current_metrics['ai_predictions'],
                errors=self.current_metrics['errors'],
                avg_latency_ms=self.current_metrics['total_latency_ms'] / total,
                cache_latency_ms=(
                    self.current_metrics['cache_latency_ms'] / self.current_metrics['cache_hits']
                    if self.current_metrics['cache_hits'] > 0 else 0.0
                ),
                ml_latency_ms=(
                    self.current_metrics['ml_latency_ms'] / self.current_metrics['ml_predictions']
                    if self.current_metrics['ml_predictions'] > 0 else 0.0
                ),
                ai_latency_ms=(
                    self.current_metrics['ai_latency_ms'] / self.current_metrics['ai_predictions']
                    if self.current_metrics['ai_predictions'] > 0 else 0.0
                ),
                estimated_cost=self.current_metrics['estimated_cost'],
                cost_saved=self.current_metrics['cost_saved']
            )

        # Add to history
        self.history.append(snapshot)

        logger.debug(
            f"[PERF_MONITOR] Snapshot created: "
            f"{total} requests, "
            f"cache={snapshot.cache_hits}/{total} ({snapshot.cache_hits/total*100:.1f}%), "
            f"cost=${snapshot.estimated_cost:.4f}, "
            f"saved=${snapshot.cost_saved:.4f}"
        )

        return snapshot

    async def _check_alerts(self):
        """Check current metrics against thresholds"""
        total = self.current_metrics['total_requests']

        if total < 10:  # Need minimum data for alerts
            return

        # Calculate rates
        cache_hit_rate = self.current_metrics['cache_hits'] / total
        error_rate = self.current_metrics['errors'] / total
        avg_latency = self.current_metrics['total_latency_ms'] / total
        ai_usage_rate = self.current_metrics['ai_predictions'] / total
        cost_per_request = self.current_metrics['estimated_cost'] / total

        # Check thresholds
        if cache_hit_rate < self.alert_thresholds['cache_hit_rate_min']:
            await self._create_alert(
                severity='warning',
                message=f"Cache hit rate below threshold: {cache_hit_rate:.1%}",
                metric='cache_hit_rate',
                value=cache_hit_rate,
                threshold=self.alert_thresholds['cache_hit_rate_min']
            )

        if error_rate > self.alert_thresholds['error_rate_max']:
            await self._create_alert(
                severity='critical',
                message=f"Error rate above threshold: {error_rate:.1%}",
                metric='error_rate',
                value=error_rate,
                threshold=self.alert_thresholds['error_rate_max']
            )

        if avg_latency > self.alert_thresholds['avg_latency_max_ms']:
            await self._create_alert(
                severity='warning',
                message=f"Average latency above threshold: {avg_latency:.0f}ms",
                metric='avg_latency_ms',
                value=avg_latency,
                threshold=self.alert_thresholds['avg_latency_max_ms']
            )

        if ai_usage_rate > self.alert_thresholds['ai_usage_rate_max']:
            await self._create_alert(
                severity='warning',
                message=f"AI API usage above threshold: {ai_usage_rate:.1%}",
                metric='ai_usage_rate',
                value=ai_usage_rate,
                threshold=self.alert_thresholds['ai_usage_rate_max']
            )

        if cost_per_request > self.alert_thresholds['cost_per_request_max']:
            await self._create_alert(
                severity='warning',
                message=f"Cost per request above threshold: ${cost_per_request:.4f}",
                metric='cost_per_request',
                value=cost_per_request,
                threshold=self.alert_thresholds['cost_per_request_max']
            )

    async def _create_alert(
        self,
        severity: str,
        message: str,
        metric: str,
        value: float,
        threshold: float
    ):
        """Create and log alert"""
        alert = Alert(
            severity=severity,
            message=message,
            metric=metric,
            value=value,
            threshold=threshold
        )

        self.alerts.append(alert)

        log_func = logger.critical if severity == 'critical' else logger.warning
        log_func(f"[PERF_ALERT] {message}")

    async def get_current_metrics(self) -> Dict[str, Any]:
        """
        Get current performance metrics

        Returns:
            Dictionary with current metrics
        """
        total = self.current_metrics['total_requests']

        if total == 0:
            return {
                'total_requests': 0,
                'cache_hit_rate': 0.0,
                'ml_usage_rate': 0.0,
                'ai_usage_rate': 0.0,
                'error_rate': 0.0,
                'avg_latency_ms': 0.0,
                'estimated_cost': 0.0,
                'cost_saved': 0.0
            }

        return {
            'total_requests': total,
            'cache_hits': self.current_metrics['cache_hits'],
            'ml_predictions': self.current_metrics['ml_predictions'],
            'ai_predictions': self.current_metrics['ai_predictions'],
            'errors': self.current_metrics['errors'],
            'cache_hit_rate': self.current_metrics['cache_hits'] / total,
            'ml_usage_rate': self.current_metrics['ml_predictions'] / total,
            'ai_usage_rate': self.current_metrics['ai_predictions'] / total,
            'error_rate': self.current_metrics['errors'] / total,
            'avg_latency_ms': self.current_metrics['total_latency_ms'] / total,
            'avg_cache_latency_ms': (
                self.current_metrics['cache_latency_ms'] / self.current_metrics['cache_hits']
                if self.current_metrics['cache_hits'] > 0 else 0.0
            ),
            'avg_ml_latency_ms': (
                self.current_metrics['ml_latency_ms'] / self.current_metrics['ml_predictions']
                if self.current_metrics['ml_predictions'] > 0 else 0.0
            ),
            'avg_ai_latency_ms': (
                self.current_metrics['ai_latency_ms'] / self.current_metrics['ai_predictions']
                if self.current_metrics['ai_predictions'] > 0 else 0.0
            ),
            'estimated_cost': self.current_metrics['estimated_cost'],
            'cost_saved': self.current_metrics['cost_saved'],
            'cost_per_request': self.current_metrics['estimated_cost'] / total,
            'roi_percentage': (
                (self.current_metrics['cost_saved'] / self.current_metrics['estimated_cost'] * 100)
                if self.current_metrics['estimated_cost'] > 0 else 0.0
            )
        }

    async def get_historical_metrics(
        self,
        time_range_minutes: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical performance metrics

        Args:
            time_range_minutes: Optional time range to filter

        Returns:
            List of historical snapshots
        """
        snapshots = list(self.history)

        if time_range_minutes:
            cutoff = datetime.utcnow() - timedelta(minutes=time_range_minutes)
            snapshots = [s for s in snapshots if s.timestamp >= cutoff]

        return [s.to_dict() for s in snapshots]

    async def get_alerts(
        self,
        severity: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get performance alerts

        Args:
            severity: Optional severity filter
            limit: Optional limit on number of alerts

        Returns:
            List of alerts
        """
        alerts = self.alerts

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        if limit:
            alerts = alerts[-limit:]

        return [
            {
                'severity': a.severity,
                'message': a.message,
                'metric': a.metric,
                'value': a.value,
                'threshold': a.threshold,
                'timestamp': a.timestamp.isoformat()
            }
            for a in alerts
        ]

    async def generate_report(
        self,
        time_range_minutes: int = 60
    ) -> Dict[str, Any]:
        """
        Generate performance report

        Args:
            time_range_minutes: Time range for report

        Returns:
            Performance report
        """
        historical = await self.get_historical_metrics(time_range_minutes)
        current = await self.get_current_metrics()
        alerts = await self.get_alerts()

        # Calculate trends if we have historical data
        trends = {}
        if len(historical) > 1:
            first = historical[0]
            last = historical[-1]

            if first['total_requests'] > 0 and last['total_requests'] > 0:
                trends = {
                    'cache_hit_rate_trend': last['cache_hit_rate'] - first['cache_hit_rate'],
                    'avg_latency_trend_ms': last['avg_latency_ms'] - first['avg_latency_ms'],
                    'cost_trend': last['estimated_cost'] - first['estimated_cost'],
                    'error_rate_trend': last['error_rate'] - first['error_rate']
                }

        return {
            'time_range_minutes': time_range_minutes,
            'generated_at': datetime.utcnow().isoformat(),
            'current_metrics': current,
            'historical_data_points': len(historical),
            'trends': trends,
            'alerts': {
                'total': len(alerts),
                'critical': len([a for a in alerts if a['severity'] == 'critical']),
                'warning': len([a for a in alerts if a['severity'] == 'warning']),
                'recent': alerts[-5:] if alerts else []
            }
        }

    async def reset(self):
        """Reset all metrics (for testing)"""
        self.current_metrics = {
            'total_requests': 0,
            'cache_hits': 0,
            'ml_predictions': 0,
            'ai_predictions': 0,
            'errors': 0,
            'total_latency_ms': 0.0,
            'cache_latency_ms': 0.0,
            'ml_latency_ms': 0.0,
            'ai_latency_ms': 0.0,
            'estimated_cost': 0.0,
            'cost_saved': 0.0
        }

        self.history.clear()
        self.alerts.clear()

        logger.info("[PERF_MONITOR] Metrics reset")

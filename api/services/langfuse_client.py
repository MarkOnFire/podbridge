"""
Langfuse Analytics Service for Editorial Assistant v3.0

Provides integration with Langfuse observability platform for:
- Real-time model usage statistics
- Per-job cost tracking
- Analytics dashboard data

Langfuse credentials are loaded from:
1. macOS Keychain (developer.workspace.LANGFUSE_*)
2. Environment variables / .env file (fallback)
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from api.services.logging import get_logger

logger = get_logger(__name__)

# Load secrets from Keychain if available
sys.path.insert(0, str(Path.home() / "Developer/the-lodge/scripts"))
try:
    from keychain_secrets import get_secret
except ImportError:
    get_secret = None


def _get_langfuse_credential(key: str) -> Optional[str]:
    """Get Langfuse credential from Keychain or environment."""
    # Try Keychain first
    if get_secret:
        value = get_secret(key)
        if value:
            return value
    # Fall back to environment
    return os.environ.get(key)


@dataclass
class ModelStats:
    """Statistics for a single model."""
    model_name: str
    request_count: int
    total_cost: float
    total_tokens: int
    avg_latency_ms: Optional[float] = None


@dataclass
class ModelStatsResponse:
    """Response containing model usage statistics."""
    models: List[ModelStats]
    period_start: datetime
    period_end: datetime
    total_cost: float
    total_requests: int


class LangfuseClient:
    """
    Client for Langfuse analytics API.

    Uses the Langfuse Python SDK to query metrics and traces.
    Also supports creating generation spans for LLM call observability.
    """

    def __init__(self):
        self._client = None
        self._initialized = False
        self._init_error: Optional[str] = None

    def _ensure_initialized(self) -> bool:
        """Lazily initialize the Langfuse client."""
        if self._initialized:
            return self._client is not None

        self._initialized = True

        public_key = _get_langfuse_credential("LANGFUSE_PUBLIC_KEY")
        secret_key = _get_langfuse_credential("LANGFUSE_SECRET_KEY")
        host = _get_langfuse_credential("LANGFUSE_BASE_URL") or "https://cloud.langfuse.com"

        if not public_key or not secret_key:
            self._init_error = "Langfuse credentials not found in Keychain or environment"
            logger.warning(self._init_error)
            return False

        try:
            from langfuse import Langfuse
            self._client = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                host=host,
            )
            logger.info(f"Langfuse client initialized (host: {host})")
            return True
        except Exception as e:
            self._init_error = f"Failed to initialize Langfuse client: {e}"
            logger.error(self._init_error)
            return False

    def is_available(self) -> bool:
        """Check if Langfuse is configured and available."""
        return self._ensure_initialized()

    def get_status(self) -> Dict[str, Any]:
        """Get Langfuse connection status."""
        available = self._ensure_initialized()
        return {
            "available": available,
            "error": self._init_error if not available else None,
            "host": _get_langfuse_credential("LANGFUSE_BASE_URL") or "https://cloud.langfuse.com",
        }

    def get_client(self):
        """Get the underlying Langfuse client for tracing.

        Returns None if not available.
        """
        if self._ensure_initialized():
            return self._client
        return None

    def trace_generation(
        self,
        name: str,
        model: str,
        input_messages: List[Dict[str, str]],
        output: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        cost: float,
        duration_ms: int,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        job_id: Optional[int] = None,
        phase: Optional[str] = None,
        tier: Optional[int] = None,
        tier_label: Optional[str] = None,
        backend: Optional[str] = None,
    ) -> Optional[str]:
        """
        Create a Langfuse generation trace for an LLM call.

        Args:
            name: Name for the generation (e.g., "analyst-generation")
            model: Model identifier
            input_messages: Input messages sent to the LLM
            output: LLM response content
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            total_tokens: Total tokens
            cost: Cost in USD
            duration_ms: Duration in milliseconds
            metadata: Additional metadata dict
            tags: List of tags for filtering
            job_id: Job ID for grouping traces
            phase: Agent phase name (analyst, formatter, seo, etc.)
            tier: Tier index (0=cheapskate, 1=default, 2=big-brain)
            tier_label: Human-readable tier name
            backend: Backend name (openrouter, etc.)

        Returns:
            Trace ID if successful, None otherwise
        """
        if not self._ensure_initialized():
            return None

        try:
            # Build trace metadata
            trace_metadata = metadata or {}
            trace_metadata.update({
                "backend": backend,
                "tier": tier,
                "tier_label": tier_label,
                "duration_ms": duration_ms,
            })

            # Build tags list
            trace_tags = tags or []
            if phase:
                trace_tags.append(f"phase:{phase}")
            if tier_label:
                trace_tags.append(f"tier:{tier_label}")
            trace_tags.append("editorial-assistant")

            # Create trace with generation
            trace = self._client.trace(
                name=f"job-{job_id}" if job_id else name,
                user_id=f"job-{job_id}" if job_id else None,
                session_id=f"session-{job_id}" if job_id else None,
                tags=trace_tags,
                metadata={"job_id": job_id, "phase": phase},
            )

            # Create generation span
            trace.generation(
                name=name,
                model=model,
                input=input_messages,
                output=output,
                usage={
                    "input": input_tokens,
                    "output": output_tokens,
                    "total": total_tokens,
                },
                metadata=trace_metadata,
                level="DEFAULT",
            )

            # Flush to ensure data is sent
            self._client.flush()

            logger.debug(f"Langfuse trace created: {trace.id} for phase={phase}, model={model}")
            return trace.id

        except Exception as e:
            logger.warning(f"Failed to create Langfuse trace: {e}")
            return None

    async def get_model_stats(
        self,
        days: int = 7,
        limit: int = 20
    ) -> Optional[ModelStatsResponse]:
        """
        Get model usage statistics from Langfuse.

        Queries the Langfuse Metrics API to get aggregated stats
        grouped by providedModelName.

        Args:
            days: Number of days to look back (default: 7)
            limit: Maximum number of models to return (default: 20)

        Returns:
            ModelStatsResponse with usage stats, or None if unavailable
        """
        if not self._ensure_initialized():
            return None

        try:
            # Calculate time range
            now = datetime.now(timezone.utc)
            period_end = now
            period_start = now - timedelta(days=days)

            # Build the metrics query for v2 API
            # Query must be JSON string for metrics_v_2.metrics()
            query = {
                "view": "observations",
                "dimensions": [{"field": "providedModelName"}],
                "metrics": [
                    {"measure": "count", "aggregation": "count"},
                    {"measure": "totalCost", "aggregation": "sum"},
                    {"measure": "totalTokens", "aggregation": "sum"},
                ],
                "filters": [],
                "fromTimestamp": period_start.isoformat(),
                "toTimestamp": period_end.isoformat(),
            }

            # Execute query via SDK v2 metrics API
            result = self._client.api.metrics_v_2.metrics(query=json.dumps(query))

            # Parse results - v2 API returns different field names
            models = []
            total_cost = 0.0
            total_requests = 0

            if result and hasattr(result, 'data'):
                for row in result.data[:limit]:
                    model_name = row.get("providedModelName") or "unknown"
                    count = int(row.get("count_count", 0))
                    cost = float(row.get("sum_totalCost", 0) or 0)
                    tokens = int(row.get("sum_totalTokens", 0) or 0)

                    models.append(ModelStats(
                        model_name=model_name,
                        request_count=count,
                        total_cost=cost,
                        total_tokens=tokens,
                        avg_latency_ms=None,  # Not available in v2 aggregation
                    ))

                    total_cost += cost
                    total_requests += count

                # Sort by cost descending
                models.sort(key=lambda m: m.total_cost, reverse=True)

            return ModelStatsResponse(
                models=models,
                period_start=period_start,
                period_end=period_end,
                total_cost=total_cost,
                total_requests=total_requests,
            )

        except Exception as e:
            logger.error(f"Failed to fetch model stats from Langfuse: {e}")
            return None

    async def get_trace_cost(self, trace_id: str) -> Optional[float]:
        """
        Get the actual cost for a specific trace.

        Used for per-job cost tracking after job completion.

        Args:
            trace_id: The Langfuse trace ID

        Returns:
            Total cost in USD, or None if not found
        """
        if not self._ensure_initialized():
            return None

        try:
            trace = self._client.api.trace.get(trace_id)
            if trace:
                # Sum up costs from all observations in the trace
                total_cost = 0.0
                if hasattr(trace, 'observations'):
                    for obs in trace.observations:
                        if hasattr(obs, 'calculated_total_cost') and obs.calculated_total_cost:
                            total_cost += float(obs.calculated_total_cost)
                return total_cost
            return None
        except Exception as e:
            logger.error(f"Failed to fetch trace cost from Langfuse: {e}")
            return None


# Module-level singleton
_langfuse_client: Optional[LangfuseClient] = None


def get_langfuse_client() -> LangfuseClient:
    """Get the singleton Langfuse client instance."""
    global _langfuse_client
    if _langfuse_client is None:
        _langfuse_client = LangfuseClient()
    return _langfuse_client

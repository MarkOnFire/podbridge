# Langfuse API and SDK Reference

Langfuse is an open-source LLM engineering platform for observability, prompt management, and evaluation.

## Core Capabilities

- **Observability**: Comprehensive tracing of LLM calls including retrieval, embedding, API calls
- **Token & Cost Tracking**: Per-request cost and token usage
- **Analytics**: Quality, cost, and latency metrics with custom dashboards
- **Prompt Management**: Version control, collaborative editing, playground testing

## API Endpoints

### Metrics API (Recommended for Analytics)

**v2 (Cloud):** `GET /api/public/v2/metrics`
**v1:** `GET /api/public/metrics`

#### Available Views
- `traces` - Trace-level aggregation
- `observations` - Observation-level data (generations, spans)
- `scores-numeric` - Numeric/boolean scores
- `scores-categorical` - String-based scores

#### Query Structure
```json
{
  "view": "observations",
  "dimensions": [{"field": "providedModelName"}],
  "metrics": [{"measure": "totalCost", "aggregation": "sum"}],
  "filters": [],
  "fromTimestamp": "2025-12-01T00:00:00Z",
  "toTimestamp": "2025-12-16T00:00:00Z",
  "orderBy": [{"field": "totalCost_sum", "direction": "desc"}]
}
```

#### Available Metrics
- `count` - Record counts
- `latency` - Duration in milliseconds
- `totalCost` - Aggregate cost in USD
- `totalTokens` - Token usage
- `timeToFirstToken` - Response latency

#### Aggregations
`sum`, `avg`, `count`, `max`, `min`, `p50`, `p75`, `p90`, `p95`, `p99`

#### Grouping Dimensions (observations)
- `providedModelName` - Model identifier (what OpenRouter actually used)
- `traceName` - Parent trace name
- `type` - Observation type (GENERATION, SPAN, EVENT)
- `environment` - Deployment environment
- `userId` - Associated user

#### Example cURL Request
```bash
curl -H "Authorization: Basic <AUTH>" \
  -G --data-urlencode 'query={...}' \
  https://cloud.langfuse.com/api/public/v2/metrics
```

#### Response Format
```json
{
  "data": [
    {
      "providedModelName": "gpt-4",
      "totalCost_sum": "150.50"
    }
  ]
}
```

## Python SDK

### Installation
```python
pip install langfuse
```

### Setup
```python
from langfuse import get_client
langfuse = get_client()  # uses LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY env vars
```

### Fetching Traces
```python
traces = langfuse.api.trace.list(
    limit=100,
    user_id="user_123",
    tags=["production"]
)
trace = langfuse.api.trace.get("traceId")
```

### Fetching Observations (v2 API - Recommended)
```python
observations = langfuse.api.observations_v_2.get_many(
    trace_id="abcdef1234",
    type="GENERATION",
    limit=100,
    fields="core,basic,usage"  # includes token/cost data
)
```

### Fetching Sessions & Scores
```python
sessions = langfuse.api.sessions.list(limit=50)
scores = langfuse.api.score_v_2.get(score_ids="ScoreId")
```

### Metrics Query (Aggregated Stats)
```python
query_v2 = {
    "view": "observations",
    "metrics": [{"measure": "totalCost", "aggregation": "sum"}],
    "dimensions": [{"field": "providedModelName"}],
    "filters": [],
    "fromTimestamp": "2025-05-01T00:00:00Z",
    "toTimestamp": "2025-05-13T00:00:00Z"
}
result = langfuse.api.metrics_v_2.get(query=query_v2)
```

### Async Support
```python
trace = await langfuse.async_api.trace.get("traceId")
```

### Common Filtering Options
- **Pagination:** `limit`, `cursor`
- **Time ranges:** `start_time`, `end_time`
- **Entity filters:** `user_id`, `session_id`, `trace_id`, `type`, `name`, `tags`, `level`

## Key URLs

- **Documentation**: https://langfuse.com/docs
- **API Reference**: https://api.reference.langfuse.com
- **OpenAPI Spec**: https://cloud.langfuse.com/generated/api/openapi.yml
- **Python SDK Reference**: https://python.reference.langfuse.com/

## Data Availability

New data becomes available for querying within 15-30 seconds of ingestion.

## Use Cases for Editorial Assistant

1. **Real-time Model Stats**: Query `providedModelName` to see which models OpenRouter actually selected
2. **Per-Job Cost Tracking**: Query by trace to get actual costs for each processing job
3. **Analytics Dashboard**: Aggregate cost/latency/token metrics over time
4. **Model Performance Comparison**: Compare latency and success rates across models

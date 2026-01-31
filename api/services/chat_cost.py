"""Chat cost tracking and analysis service.

Provides functionality to:
- Track per-message and per-session costs
- Compare chat costs vs automated pipeline costs
- Generate cost statistics for model right-sizing decisions
- Export cost data for viability assessment
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from api.models.chat import (
    CostComparisonResponse,
    SessionStatsResponse,
)
from api.services import database


async def get_session_stats(session_id: str) -> Optional[SessionStatsResponse]:
    """Get detailed cost and usage statistics for a chat session.

    Args:
        session_id: Session UUID

    Returns:
        SessionStatsResponse with detailed metrics or None if session not found
    """
    session = await database.get_chat_session(session_id)
    if not session:
        return None

    messages = await database.get_session_messages(session_id)

    # Separate by role
    user_messages = [m for m in messages if m.role == "user"]
    assistant_messages = [m for m in messages if m.role == "assistant"]

    # Calculate averages
    total_response_tokens = sum(m.tokens or 0 for m in assistant_messages)
    total_response_cost = sum(m.cost or 0.0 for m in assistant_messages)
    assistant_count = len(assistant_messages)

    avg_response_tokens = total_response_tokens / assistant_count if assistant_count > 0 else 0.0
    avg_response_cost = total_response_cost / assistant_count if assistant_count > 0 else 0.0

    # Get unique models used
    models_used = list(set(m.model for m in assistant_messages if m.model))

    # Calculate session duration
    if messages:
        first_msg = min(m.created_at for m in messages if m.created_at)
        last_msg = max(m.created_at for m in messages if m.created_at)
        duration_minutes = (last_msg - first_msg).total_seconds() / 60.0
    else:
        duration_minutes = 0.0

    return SessionStatsResponse(
        session_id=session_id,
        total_cost=session.total_cost,
        total_tokens=session.total_tokens,
        message_count=session.message_count,
        user_messages=len(user_messages),
        assistant_messages=assistant_count,
        models_used=models_used,
        avg_response_tokens=avg_response_tokens,
        avg_response_cost=avg_response_cost,
        duration_minutes=duration_minutes,
    )


async def get_cost_comparison(job_id: int) -> Optional[CostComparisonResponse]:
    """Compare costs between automated phases and chat sessions for a job.

    This is the key metric for assessing embedded chat viability vs Claude Max.

    Args:
        job_id: Job ID to analyze

    Returns:
        CostComparisonResponse with breakdown or None if job not found
    """
    job = await database.get_job(job_id)
    if not job:
        return None

    # Extract automated phase costs from job phases
    automated_phases = {}
    if job.phases:
        for phase in job.phases:
            if phase.cost is not None and phase.cost > 0:
                automated_phases[phase.name] = {
                    "cost": phase.cost,
                    "tokens": phase.tokens or 0,
                    "model": phase.model,
                    "tier": phase.tier_label,
                }

    # Get chat session costs
    sessions = await database.list_sessions_for_job(job_id, include_cleared=False)
    chat_sessions = []
    for session in sessions:
        chat_sessions.append(
            {
                "id": session.id,
                "cost": session.total_cost,
                "tokens": session.total_tokens,
                "messages": session.message_count,
                "model": session.model,
                "created_at": session.created_at.isoformat() if session.created_at else None,
            }
        )

    # Calculate totals
    automated_total = sum(p.get("cost", 0) for p in automated_phases.values())
    chat_total = sum(s.get("cost", 0) for s in chat_sessions)

    return CostComparisonResponse(
        job_id=job_id,
        automated_phases=automated_phases,
        chat_sessions=chat_sessions,
        totals={
            "automated": round(automated_total, 4),
            "chat": round(chat_total, 4),
            "combined": round(automated_total + chat_total, 4),
        },
    )


async def get_model_cost_breakdown(
    job_ids: Optional[List[int]] = None,
    days_back: int = 30,
) -> Dict[str, Any]:
    """Get cost breakdown by model across chat sessions.

    Useful for model right-sizing decisions - shows avg cost/token per model.

    Args:
        job_ids: Optional list of job IDs to analyze (None = all)
        days_back: How many days of history to include

    Returns:
        Dictionary with per-model statistics
    """
    from datetime import timedelta

    # This would need to query across all sessions and messages
    # For now, return structure that will be populated when called
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)

    # Get all recent sessions
    async with database.get_session() as session:
        from sqlalchemy import select

        stmt = select(database.chat_sessions_table).where(database.chat_sessions_table.c.created_at >= cutoff_date)

        if job_ids:
            stmt = stmt.where(database.chat_sessions_table.c.job_id.in_(job_ids))

        result = await session.execute(stmt)
        sessions = result.fetchall()

    # Aggregate by model
    model_stats: Dict[str, Dict[str, Any]] = {}

    for sess in sessions:
        # Get messages for this session
        messages = await database.get_session_messages(sess.id)

        for msg in messages:
            if msg.role == "assistant" and msg.model and msg.cost is not None:
                model = msg.model

                if model not in model_stats:
                    model_stats[model] = {
                        "total_cost": 0.0,
                        "total_tokens": 0,
                        "response_count": 0,
                        "sessions": set(),
                    }

                model_stats[model]["total_cost"] += msg.cost
                model_stats[model]["total_tokens"] += msg.tokens or 0
                model_stats[model]["response_count"] += 1
                model_stats[model]["sessions"].add(sess.id)

    # Calculate averages and format output
    result = {}
    for model, stats in model_stats.items():
        response_count = stats["response_count"]
        result[model] = {
            "total_cost": round(stats["total_cost"], 4),
            "total_tokens": stats["total_tokens"],
            "response_count": response_count,
            "session_count": len(stats["sessions"]),
            "avg_cost_per_response": round(stats["total_cost"] / response_count, 6) if response_count > 0 else 0,
            "avg_tokens_per_response": round(stats["total_tokens"] / response_count, 1) if response_count > 0 else 0,
            "cost_per_1k_tokens": (
                round((stats["total_cost"] / stats["total_tokens"]) * 1000, 4) if stats["total_tokens"] > 0 else 0
            ),
        }

    return {
        "period_days": days_back,
        "models": result,
        "total_sessions_analyzed": len(sessions),
    }


async def estimate_session_cost(
    message_count: int,
    model: str = "claude-sonnet-4-20250514",
) -> Dict[str, float]:
    """Estimate cost for a chat session based on historical data.

    Useful for showing users expected costs before starting a session.

    Args:
        message_count: Expected number of back-and-forth exchanges
        model: Model to use for estimates

    Returns:
        Dictionary with estimated costs
    """
    # Get historical stats for this model
    model_breakdown = await get_model_cost_breakdown(days_back=30)

    model_data = model_breakdown.get("models", {}).get(model, None)

    if model_data:
        # Use historical averages
        avg_cost = model_data["avg_cost_per_response"]
        avg_tokens = model_data["avg_tokens_per_response"]
    else:
        # Default estimates based on typical Claude pricing
        # These are rough estimates - adjust based on actual usage
        avg_cost = 0.01  # $0.01 per response as baseline
        avg_tokens = 500

    estimated_cost = avg_cost * message_count
    estimated_tokens = int(avg_tokens * message_count)

    return {
        "estimated_cost": round(estimated_cost, 4),
        "estimated_tokens": estimated_tokens,
        "message_count": message_count,
        "model": model,
        "based_on_historical": model_data is not None,
        "note": "Actual costs may vary based on response length and complexity",
    }


async def get_cost_summary_for_period(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Get overall chat cost summary for a time period.

    Useful for monthly billing analysis and viability assessment.

    Args:
        start_date: Start of period (None = 30 days ago)
        end_date: End of period (None = now)

    Returns:
        Dictionary with period cost summary
    """
    from datetime import timedelta

    if end_date is None:
        end_date = datetime.now(timezone.utc)
    if start_date is None:
        start_date = end_date - timedelta(days=30)

    # Query all sessions in period
    async with database.get_session() as session:
        from sqlalchemy import and_, select

        stmt = select(database.chat_sessions_table).where(
            and_(
                database.chat_sessions_table.c.created_at >= start_date,
                database.chat_sessions_table.c.created_at <= end_date,
            )
        )

        result = await session.execute(stmt)
        sessions = result.fetchall()

    total_cost = sum(s.total_cost for s in sessions)
    total_tokens = sum(s.total_tokens for s in sessions)
    total_messages = sum(s.message_count for s in sessions)

    unique_jobs = len(set(s.job_id for s in sessions))

    return {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "days": (end_date - start_date).days,
        },
        "totals": {
            "cost": round(total_cost, 4),
            "tokens": total_tokens,
            "messages": total_messages,
            "sessions": len(sessions),
            "unique_jobs": unique_jobs,
        },
        "averages": {
            "cost_per_session": round(total_cost / len(sessions), 4) if sessions else 0,
            "cost_per_job": round(total_cost / unique_jobs, 4) if unique_jobs > 0 else 0,
            "messages_per_session": round(total_messages / len(sessions), 1) if sessions else 0,
        },
        "breakeven_analysis": {
            "claude_max_monthly": 20.00,
            "current_monthly_projection": round(total_cost * (30 / max((end_date - start_date).days, 1)), 2),
            "jobs_at_current_rate": unique_jobs,
        },
    }

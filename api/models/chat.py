"""Chat models for Editorial Assistant v3.0 API."""
from pydantic import BaseModel, Field
from typing import Optional, List


class ChatMessage(BaseModel):
    """Single message in conversation."""
    role: str = Field(..., description="Message role: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request to send a chat message."""
    message: str = Field(..., description="User message to send")
    project_name: Optional[str] = Field(None, description="Project context for the chat")
    conversation_history: List[ChatMessage] = Field(
        default_factory=list,
        description="Previous messages in the conversation"
    )


class ChatResponse(BaseModel):
    """Response from chat endpoint."""
    response: str = Field(..., description="Assistant's response")
    tokens_used: int = Field(..., description="Total tokens used in request/response")
    cost: float = Field(..., description="Cost in USD for this chat turn")
    model: str = Field(..., description="Model used (e.g., 'claude-3-5-sonnet-20241022')")

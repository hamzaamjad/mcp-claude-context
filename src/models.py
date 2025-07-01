"""Pydantic models for Claude conversation data."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class MessageRole(str, Enum):
    """Message role in a conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageContent(BaseModel):
    """Content within a message."""
    type: str = Field(..., description="Content type (text, image, etc.)")
    text: Optional[str] = Field(None, description="Text content if type is text")
    image_url: Optional[HttpUrl] = Field(None, description="Image URL if type is image")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ConversationMessage(BaseModel):
    """Individual message in a conversation."""
    id: str = Field(..., description="Unique message ID")
    role: MessageRole = Field(..., description="Message sender role")
    content: List[MessageContent] = Field(..., description="Message content")
    created_at: datetime = Field(..., description="Message creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    parent_id: Optional[str] = Field(None, description="Parent message ID for threaded conversations")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional message metadata")


class ConversationMetadata(BaseModel):
    """Metadata about a conversation."""
    model: Optional[str] = Field(None, description="Claude model used")
    temperature: Optional[float] = Field(None, description="Temperature setting")
    max_tokens: Optional[int] = Field(None, description="Max tokens setting")
    tags: List[str] = Field(default_factory=list, description="User-defined tags")
    shared: bool = Field(False, description="Whether conversation is shared")
    archived: bool = Field(False, description="Whether conversation is archived")


class Conversation(BaseModel):
    """Complete conversation data."""
    id: str = Field(..., description="Unique conversation ID")
    title: Optional[str] = Field(None, description="Conversation title")
    messages: List[ConversationMessage] = Field(..., description="List of messages")
    created_at: datetime = Field(..., description="Conversation creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    metadata: ConversationMetadata = Field(default_factory=ConversationMetadata, description="Conversation metadata")
    url: Optional[HttpUrl] = Field(None, description="Claude.ai URL for this conversation")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConversationSummary(BaseModel):
    """Summary of a conversation for listing."""
    id: str = Field(..., description="Unique conversation ID")
    title: Optional[str] = Field(None, description="Conversation title")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    message_count: int = Field(..., description="Number of messages")
    url: Optional[HttpUrl] = Field(None, description="Claude.ai URL")
    preview: Optional[str] = Field(None, description="Preview of last message")


class ExtractionResult(BaseModel):
    """Result of a conversation extraction operation."""
    success: bool = Field(..., description="Whether extraction was successful")
    conversation: Optional[Conversation] = Field(None, description="Extracted conversation data")
    error: Optional[str] = Field(None, description="Error message if extraction failed")
    timestamp: datetime = Field(default_factory=datetime.now, description="Extraction timestamp")


class ExtractionConfig(BaseModel):
    """Configuration for extraction operations."""
    session_key: Optional[str] = Field(None, description="Session key for authentication")
    timeout: int = Field(30, description="Extraction timeout in seconds")
    retry_count: int = Field(3, description="Number of retries on failure")
    retry_delay: float = Field(1.0, description="Initial retry delay in seconds")
    headless: bool = Field(True, description="Run browser in headless mode")
    user_agent: Optional[str] = Field(None, description="Custom user agent string")
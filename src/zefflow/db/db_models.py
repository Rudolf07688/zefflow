from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user")
    data_sources: Mapped[list["DataSource"]] = relationship(back_populates="user")


class DataSource(Base):
    """A configured database connection a user can query (BigQuery, Postgres, etc.)."""

    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # bigquery | postgres | redshift
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    user: Mapped["User"] = relationship(back_populates="data_sources")
    query_executions: Mapped[list["QueryExecution"]] = relationship(back_populates="data_source")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    user: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", order_by="Message.created_at")
    errors: Mapped[list["AgentError"]] = relationship(back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user | assistant | system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    agent_response: Mapped["AgentResponse | None"] = relationship(back_populates="message", uselist=False)


class AgentResponse(Base):
    """Metadata for a single LLM completion (one assistant turn)."""

    __tablename__ = "agent_responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    stop_reason: Mapped[str | None] = mapped_column(String(50))  # end_turn | tool_use | max_tokens
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    message: Mapped["Message"] = relationship(back_populates="agent_response")
    tool_calls: Mapped[list["ToolCall"]] = relationship(back_populates="agent_response", order_by="ToolCall.created_at")


class ToolCall(Base):
    """A single tool invocation within an agent response."""

    __tablename__ = "tool_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_response_id: Mapped[int] = mapped_column(ForeignKey("agent_responses.id"), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    input: Mapped[dict | None] = mapped_column(JSONB)
    output: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="success")  # success | error
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    agent_response: Mapped["AgentResponse"] = relationship(back_populates="tool_calls")
    query_execution: Mapped["QueryExecution | None"] = relationship(back_populates="tool_call", uselist=False)


class QueryExecution(Base):
    """A SQL query run against a DataSource, linked to the ToolCall that triggered it."""

    __tablename__ = "query_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tool_call_id: Mapped[int] = mapped_column(ForeignKey("tool_calls.id"), nullable=False)
    data_source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    sql_query: Mapped[str] = mapped_column(Text, nullable=False)
    row_count: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    tool_call: Mapped["ToolCall"] = relationship(back_populates="query_execution")
    data_source: Mapped["DataSource"] = relationship(back_populates="query_executions")


class AgentError(Base):
    """Runtime errors surfaced during agent execution."""

    __tablename__ = "agent_errors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), nullable=False)
    agent_response_id: Mapped[int | None] = mapped_column(ForeignKey("agent_responses.id"))
    error_type: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    traceback: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    conversation: Mapped["Conversation"] = relationship(back_populates="errors")

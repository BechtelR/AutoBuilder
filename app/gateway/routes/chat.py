"""Chat routes — conversational Director interface."""

import uuid
from typing import Annotated

from arq.connections import ArqRedis
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_201_CREATED

from app.db.models import Chat, ChatMessage
from app.gateway.deps import get_arq_pool, get_db_session
from app.gateway.models.chat import (
    ChatMessageResponse,
    ChatResponse,
    CreateChatRequest,
    SendChatMessageRequest,
)
from app.lib import NotFoundError
from app.models.constants import SYSTEM_USER_ID
from app.models.enums import ChatMessageRole, ChatStatus, ChatType

router = APIRouter(tags=["chat"])

MAIN_SESSION_PREFIX = "main_"
SETTINGS_SESSION_PREFIX = "settings_"

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
ArqPool = Annotated[ArqRedis, Depends(get_arq_pool)]


@router.post("/chat", status_code=HTTP_201_CREATED)
async def create_chat(
    request: CreateChatRequest,
    session: DbSession,
) -> ChatResponse:
    """Create a new chat session."""
    chat = Chat(
        session_id=str(uuid.uuid4()),
        type=request.type,
        title=request.title,
        project_id=request.project_id,
    )
    session.add(chat)
    await session.commit()
    await session.refresh(chat)

    return _chat_to_response(chat)


@router.get("/chat")
async def list_chats(
    session: DbSession,
    type: Annotated[ChatType | None, Query()] = None,
    status: Annotated[ChatStatus | None, Query()] = None,
) -> list[ChatResponse]:
    """List chat sessions with optional filters."""
    stmt = select(Chat).order_by(Chat.created_at.desc())
    if type is not None:
        stmt = stmt.where(Chat.type == type)
    if status is not None:
        stmt = stmt.where(Chat.status == status)

    result = await session.execute(stmt)
    chats = result.scalars().all()
    return [_chat_to_response(c) for c in chats]


# ---------------------------------------------------------------------------
# Well-known session auto-creation (must be before {session_id} routes)
# ---------------------------------------------------------------------------


@router.get("/chat/main")
async def get_or_create_main_session(
    session: DbSession,
) -> ChatResponse:
    """Get or auto-create the Main chat session for the system user."""
    chat = await _ensure_well_known_session(
        session,
        f"{MAIN_SESSION_PREFIX}{SYSTEM_USER_ID}",
        ChatType.DIRECTOR,
        "Main",
    )
    return _chat_to_response(chat)


@router.get("/chat/settings")
async def get_or_create_settings_session(
    session: DbSession,
) -> ChatResponse:
    """Get or auto-create the Settings chat session for the system user."""
    chat = await _ensure_well_known_session(
        session,
        f"{SETTINGS_SESSION_PREFIX}{SYSTEM_USER_ID}",
        ChatType.SETTINGS,
        "Settings",
    )
    return _chat_to_response(chat)


@router.get("/chat/{session_id}")
async def get_chat(
    session_id: str,
    session: DbSession,
) -> ChatResponse:
    """Get a chat session by session ID."""
    chat = await _get_chat_by_session_id(session, session_id)
    return _chat_to_response(chat)


@router.post("/chat/{session_id}/messages", status_code=HTTP_201_CREATED)
async def send_message(
    session_id: str,
    request: SendChatMessageRequest,
    session: DbSession,
    arq_pool: ArqPool,
) -> ChatMessageResponse:
    """Send a user message and enqueue a Director turn."""
    chat = await _get_chat_by_session_id(session, session_id)

    message = ChatMessage(
        chat_id=chat.id,
        role=ChatMessageRole.USER,
        content=request.content,
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)

    # Enqueue Director turn for async processing
    await arq_pool.enqueue_job(  # type: ignore[reportUnknownMemberType]
        "run_director_turn",
        str(chat.id),
        str(message.id),
    )

    return _message_to_response(message)


@router.get("/chat/{session_id}/messages")
async def get_messages(
    session_id: str,
    session: DbSession,
) -> list[ChatMessageResponse]:
    """Retrieve message history for a chat session."""
    chat = await _get_chat_by_session_id(session, session_id)

    stmt = (
        select(ChatMessage).where(ChatMessage.chat_id == chat.id).order_by(ChatMessage.created_at)
    )
    result = await session.execute(stmt)
    messages = result.scalars().all()
    return [_message_to_response(m) for m in messages]


# ---------------------------------------------------------------------------
# SSE placeholder — full implementation with real streaming
# ---------------------------------------------------------------------------


@router.get("/chat/{session_id}/stream")
async def chat_stream(
    session_id: str,
    session: DbSession,
) -> ChatResponse:
    """Placeholder for SSE streaming of Director responses.

    Returns the chat detail for now. Real SSE implementation arrives when
    streaming is wired up.
    """
    chat = await _get_chat_by_session_id(session, session_id)
    return _chat_to_response(chat)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _ensure_well_known_session(
    session: AsyncSession,
    session_id: str,
    chat_type: ChatType,
    title: str,
) -> Chat:
    """Get or create a well-known chat session (Main, Settings).

    Handles concurrent creation race by catching unique constraint violations
    and re-reading the existing row.
    """
    from sqlalchemy.exc import IntegrityError

    result = await session.execute(select(Chat).where(Chat.session_id == session_id))
    chat = result.scalar_one_or_none()
    if chat is not None:
        return chat

    chat = Chat(
        session_id=session_id,
        type=chat_type,
        status=ChatStatus.ACTIVE,
        title=title,
    )
    session.add(chat)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        result = await session.execute(select(Chat).where(Chat.session_id == session_id))
        existing = result.scalar_one_or_none()
        if existing is not None:
            return existing
        raise
    await session.refresh(chat)
    return chat


async def _get_chat_by_session_id(session: AsyncSession, session_id: str) -> Chat:
    """Load a chat by session_id or raise NotFoundError."""
    result = await session.execute(select(Chat).where(Chat.session_id == session_id))
    chat = result.scalar_one_or_none()
    if chat is None:
        raise NotFoundError(message=f"Chat session '{session_id}' not found")
    return chat


def _chat_to_response(chat: Chat) -> ChatResponse:
    """Convert a Chat ORM model to a ChatResponse."""
    return ChatResponse(
        id=str(chat.id),
        session_id=chat.session_id,
        type=chat.type,
        status=chat.status,
        title=chat.title,
        project_id=str(chat.project_id) if chat.project_id is not None else None,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
    )


def _message_to_response(msg: ChatMessage) -> ChatMessageResponse:
    """Convert a ChatMessage ORM model to a ChatMessageResponse."""
    return ChatMessageResponse(
        id=str(msg.id),
        chat_id=str(msg.chat_id),
        role=msg.role,
        content=msg.content,
        created_at=msg.created_at,
    )

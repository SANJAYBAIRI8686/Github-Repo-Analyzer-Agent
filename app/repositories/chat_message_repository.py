from __future__ import annotations

from sqlalchemy import select

from app.models.chat_message import ChatMessage
from app.repositories.base import BaseRepository


class ChatMessageRepository(BaseRepository[ChatMessage]):
    def list_recent(self, chat_session_id: int, limit: int) -> list[ChatMessage]:
        statement = (
            select(ChatMessage)
            .where(ChatMessage.chat_session_id == chat_session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def create(self, *, chat_session_id: int, role: str, content: str, citations: list | None = None) -> ChatMessage:
        message = ChatMessage(chat_session_id=chat_session_id, role=role, content=content, citations=citations)
        return self.add(message)
from __future__ import annotations

from sqlalchemy import select

from app.models.chat_session import ChatSession
from app.repositories.base import BaseRepository


class ChatSessionRepository(BaseRepository[ChatSession]):
    def get_by_id(self, session_id: int) -> ChatSession | None:
        return self.session.get(ChatSession, session_id)

    def list_by_repository(self, repository_id: int) -> list[ChatSession]:
        statement = select(ChatSession).where(ChatSession.repository_id == repository_id).order_by(ChatSession.updated_at.desc())
        return list(self.session.scalars(statement))

    def create(self, *, repository_id: int, user_id: int | None = None, title: str | None = None) -> ChatSession:
        chat_session = ChatSession(repository_id=repository_id, user_id=user_id, title=title)
        return self.add(chat_session)
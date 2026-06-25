from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import db_dep, get_current_user, settings_dep
from app.core.config import Settings
from app.models.user import User
from app.schemas.intelligence import (
    AnalysisResponse,
    ChatRequest,
    ChatResponse,
    ChatSessionCreateRequest,
    DependencyResponse,
    ExplainRequest,
    ExplainResponse,
    FileSummaryResponse,
    OverviewResponse,
    SearchRequest,
    SearchResponse,
    ChatSessionRead,
    ChatMessageRead,
)
from app.services.intelligence import RepositoryIntelligenceService


router = APIRouter(tags=["intelligence"])


def _service(db: Session, settings: Settings) -> RepositoryIntelligenceService:
    return RepositoryIntelligenceService(db, settings)


@router.post("/repos/{repository_id}/chat")
def chat(
    repository_id: int,
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_dep),
    settings: Settings = Depends(settings_dep),
):
    service = _service(db, settings)
    chat_session, citations, stream = service.build_chat_stream(
        repository_id,
        current_user.id,
        payload.message,
        session_id=payload.session_id,
        file_path=payload.file_path,
        language=payload.language,
        symbol_name=payload.symbol_name,
    )
    response = StreamingResponse(stream, media_type="text/plain; charset=utf-8")
    response.headers["X-Chat-Session-Id"] = str(chat_session.id)
    response.headers["X-Chat-Citation-Count"] = str(len(citations))
    return response


@router.post("/repos/{repository_id}/search", response_model=SearchResponse)
def search(
    repository_id: int,
    payload: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_dep),
    settings: Settings = Depends(settings_dep),
) -> SearchResponse:
    return _service(db, settings).search(
        repository_id,
        payload.query,
        file_path=payload.file_path,
        language=payload.language,
        symbol_name=payload.symbol_name,
        top_k=payload.top_k,
    )


@router.get("/repos/{repository_id}/overview", response_model=OverviewResponse)
def overview(
    repository_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_dep),
    settings: Settings = Depends(settings_dep),
) -> OverviewResponse:
    return _service(db, settings).build_overview(repository_id)


@router.get("/repos/{repository_id}/deps", response_model=DependencyResponse)
def dependencies(
    repository_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_dep),
    settings: Settings = Depends(settings_dep),
) -> DependencyResponse:
    return _service(db, settings).analyze_dependencies(repository_id)


@router.get("/repos/{repository_id}/files/{file_path:path}/summary", response_model=FileSummaryResponse)
def file_summary(
    repository_id: int,
    file_path: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_dep),
    settings: Settings = Depends(settings_dep),
) -> FileSummaryResponse:
    return _service(db, settings).file_summary_or_create(repository_id, file_path)


@router.get("/repos/{repository_id}/sessions", response_model=list[ChatSessionRead])
def list_sessions(
    repository_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_dep),
    settings: Settings = Depends(settings_dep),
) -> list[ChatSessionRead]:
    return _service(db, settings).list_chat_sessions(repository_id)


@router.post("/repos/{repository_id}/sessions", response_model=ChatSessionRead)
def create_session(
    repository_id: int,
    payload: ChatSessionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_dep),
    settings: Settings = Depends(settings_dep),
) -> ChatSessionRead:
    return _service(db, settings).create_chat_session(repository_id, current_user.id, payload.title)


@router.get("/repos/{repository_id}/sessions/{session_id}", response_model=list[ChatMessageRead])
def session_history(
    repository_id: int,
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_dep),
    settings: Settings = Depends(settings_dep),
) -> list[ChatMessageRead]:
    return _service(db, settings).list_chat_history(repository_id, session_id)


@router.post("/explain", response_model=ExplainResponse)
def explain(
    payload: ExplainRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_dep),
    settings: Settings = Depends(settings_dep),
) -> ExplainResponse:
    return _service(db, settings).explain(payload)


@router.post("/repos/{repository_id}/bugs", response_model=AnalysisResponse)
def bugs(
    repository_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_dep),
    settings: Settings = Depends(settings_dep),
) -> AnalysisResponse:
    return _service(db, settings).detect_bugs(repository_id)


@router.post("/repos/{repository_id}/security", response_model=AnalysisResponse)
def security(
    repository_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_dep),
    settings: Settings = Depends(settings_dep),
) -> AnalysisResponse:
    return _service(db, settings).audit_security(repository_id)

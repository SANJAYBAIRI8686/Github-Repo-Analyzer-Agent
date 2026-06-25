from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import db_dep, get_current_user, settings_dep
from app.core.config import Settings
from app.models.user import User
from app.schemas.delivery import (
    ArchitectureDiagramResponse,
    DocumentationBundleResponse,
    HealthResponse,
    OnboardingLessonResponse,
    OnboardingResponse,
)
from app.services.delivery import DeliveryService


router = APIRouter(tags=["delivery"])


def _service(db: Session, settings: Settings) -> DeliveryService:
    return DeliveryService(db, settings)


@router.post("/repos/{repository_id}/docs/generate", response_model=DocumentationBundleResponse)
def generate_docs(
    repository_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_dep),
    settings: Settings = Depends(settings_dep),
) -> DocumentationBundleResponse:
    return _service(db, settings).generate_docs(repository_id, request.app.openapi())


@router.get("/repos/{repository_id}/docs/download")
def download_docs(
    repository_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_dep),
    settings: Settings = Depends(settings_dep),
):
    bundle = _service(db, settings).docs_zip(repository_id, request.app.openapi())
    return Response(
        content=bundle,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="repo-{repository_id}-docs.zip"'},
    )


@router.get("/repos/{repository_id}/health", response_model=HealthResponse)
def health(
    repository_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_dep),
    settings: Settings = Depends(settings_dep),
) -> HealthResponse:
    return _service(db, settings).health(repository_id)


@router.get("/repos/{repository_id}/architecture", response_model=ArchitectureDiagramResponse)
def architecture(
    repository_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_dep),
    settings: Settings = Depends(settings_dep),
) -> ArchitectureDiagramResponse:
    return _service(db, settings).architecture_diagram(repository_id)


@router.get("/repos/{repository_id}/onboarding", response_model=OnboardingResponse)
def onboarding(
    repository_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_dep),
    settings: Settings = Depends(settings_dep),
) -> OnboardingResponse:
    return _service(db, settings).onboarding(repository_id)


@router.get("/repos/{repository_id}/onboarding/{lesson_slug}", response_model=OnboardingLessonResponse)
def onboarding_lesson(
    repository_id: int,
    lesson_slug: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_dep),
    settings: Settings = Depends(settings_dep),
) -> OnboardingLessonResponse:
    return _service(db, settings).onboarding_lesson(repository_id, lesson_slug)

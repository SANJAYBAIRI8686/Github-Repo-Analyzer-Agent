from __future__ import annotations

from pydantic import BaseModel


class GeneratedDocumentRead(BaseModel):
    filename: str
    content: str


class DocumentationBundleResponse(BaseModel):
    repository_id: int
    files: list[GeneratedDocumentRead]
    download_url: str


class HealthCategoryRead(BaseModel):
    name: str
    score: int
    max_score: int
    stars: float
    rationale: str
    signals: list[str]


class HealthResponse(BaseModel):
    repository_id: int
    overall_score: int
    overall_stars: float
    categories: list[HealthCategoryRead]


class ArchitectureDiagramResponse(BaseModel):
    repository_id: int
    diagram_format: str
    diagram_source: str
    explanation: str


class OnboardingLessonRead(BaseModel):
    slug: str
    title: str
    objective: str
    summary: str
    file_refs: list[str]
    checkpoint_question: str
    checkpoint_hint: str


class OnboardingResponse(BaseModel):
    repository_id: int
    lessons: list[OnboardingLessonRead]


class OnboardingLessonResponse(BaseModel):
    repository_id: int
    lesson: OnboardingLessonRead

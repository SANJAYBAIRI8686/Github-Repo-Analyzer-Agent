from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: int | None = None
    file_path: str | None = None
    language: str | None = None
    symbol_name: str | None = None


class ChatSessionCreateRequest(BaseModel):
    title: str | None = None


class ChatCitation(BaseModel):
    file_path: str
    line_start: int | None = None
    line_end: int | None = None
    symbol_name: str | None = None


class ChatResponse(BaseModel):
    session_id: int
    answer: str
    citations: list[ChatCitation]


class ChatSessionRead(ORMModel):
    id: int
    repository_id: int
    user_id: int | None
    title: str | None
    created_at: datetime
    updated_at: datetime


class ChatMessageRead(ORMModel):
    id: int
    chat_session_id: int
    role: str
    content: str
    citations: list[dict[str, Any]] | None
    created_at: datetime


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    file_path: str | None = None
    language: str | None = None
    symbol_name: str | None = None
    top_k: int | None = None


class SearchHitRead(BaseModel):
    chunk_id: str
    file_path: str | None
    language: str | None
    symbol_name: str | None
    start_line: int | None
    end_line: int | None
    snippet: str
    score: float | None
    citation: str


class SearchResponse(BaseModel):
    repository_id: int
    query: str
    hits: list[SearchHitRead]


class OverviewResponse(BaseModel):
    repository_id: int
    project_name: str | None
    purpose: str | None
    main_language: str | None
    framework: str | None
    file_count: int
    dependencies: list[str]
    architecture_summary: str | None
    complexity: str | None
    learning_difficulty: str | None
    folder_explanations: dict[str, str]


class FileSummaryResponse(BaseModel):
    repository_id: int
    file_path: str
    summary: str


class DependencyRead(BaseModel):
    name: str
    spec: str | None = None
    description: str
    why_used: str
    source_file: str | None = None


class DependencyResponse(BaseModel):
    repository_id: int
    dependencies: list[DependencyRead]


class ExplainRequest(BaseModel):
    repo_id: int | None = None
    code: str | None = None
    symbol_name: str | None = None
    file_path: str | None = None
    language: str | None = None


class ExplainResponse(BaseModel):
    purpose: str
    inputs: list[str]
    outputs: list[str]
    complexity: str
    improvements: list[str]
    citations: list[str]


class FindingRead(BaseModel):
    severity: str
    title: str
    details: str
    file_path: str | None = None
    line: int | None = None
    kind: str


class AnalysisResponse(BaseModel):
    repository_id: int
    findings: list[FindingRead]

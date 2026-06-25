from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import NotFoundError
from app.models.repository import Repository
from app.rag.retrieval import RepositoryRetrievalEngine
from app.schemas.delivery import (
    ArchitectureDiagramResponse,
    DocumentationBundleResponse,
    GeneratedDocumentRead,
    HealthCategoryRead,
    HealthResponse,
    OnboardingLessonRead,
    OnboardingLessonResponse,
    OnboardingResponse,
)
from app.services.intelligence import RepositoryIntelligenceService
from app.services.vector_store import ChromaVectorStore


@dataclass(slots=True)
class DeliveryService:
    session: Session
    settings: Settings

    def __post_init__(self) -> None:
        self.vector_store = ChromaVectorStore(self.settings.chroma_persist_dir)
        self.retrieval = RepositoryRetrievalEngine(self.vector_store, self.settings)
        self.intelligence = RepositoryIntelligenceService(self.session, self.settings)

    def get_repository(self, repository_id: int) -> Repository:
        return self.intelligence.get_repository(repository_id)

    def generate_docs(self, repository_id: int, openapi_schema: dict | None = None) -> DocumentationBundleResponse:
        repository = self.get_repository(repository_id)
        overview = self.intelligence.build_overview(repository.id)
        dependencies = self.intelligence.analyze_dependencies(repository.id).dependencies
        architecture = self.architecture_diagram(repository.id)
        docs = [
            GeneratedDocumentRead(filename="README.md", content=self._readme(repository, overview, dependencies)),
            GeneratedDocumentRead(filename="Architecture.md", content=self._architecture_markdown(repository, architecture.diagram_source)),
            GeneratedDocumentRead(filename="API.md", content=self._api_markdown(repository, openapi_schema)),
            GeneratedDocumentRead(filename="Developer_Guide.md", content=self._developer_guide(repository, overview)),
            GeneratedDocumentRead(filename="Installation_Guide.md", content=self._installation_guide(repository)),
            GeneratedDocumentRead(filename="Contribution_Guide.md", content=self._contribution_guide(repository)),
        ]
        return DocumentationBundleResponse(
            repository_id=repository.id,
            files=docs,
            download_url=f"/repos/{repository.id}/docs/download",
        )

    def docs_zip(self, repository_id: int, openapi_schema: dict | None = None) -> bytes:
        bundle = self.generate_docs(repository_id, openapi_schema)
        buffer = BytesIO()
        with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
            for item in bundle.files:
                archive.writestr(item.filename, item.content)
        return buffer.getvalue()

    def health(self, repository_id: int) -> HealthResponse:
        repository = self.get_repository(repository_id)
        docs_score, docs_rationale, docs_signals = self._documentation_score(repository)
        test_score, test_rationale, test_signals = self._testing_score(repository)
        architecture_score, architecture_rationale, architecture_signals = self._architecture_score(repository)
        security_score, security_rationale, security_signals = self._security_score(repository)
        maintainability_score, maintainability_rationale, maintainability_signals = self._maintainability_score(repository)
        performance_score, performance_rationale, performance_signals = self._performance_score(repository)
        categories = [
            HealthCategoryRead(name="Documentation", score=docs_score, max_score=20, stars=self._stars(docs_score, 20), rationale=docs_rationale, signals=docs_signals),
            HealthCategoryRead(name="Testing", score=test_score, max_score=15, stars=self._stars(test_score, 15), rationale=test_rationale, signals=test_signals),
            HealthCategoryRead(name="Architecture", score=architecture_score, max_score=20, stars=self._stars(architecture_score, 20), rationale=architecture_rationale, signals=architecture_signals),
            HealthCategoryRead(name="Security", score=security_score, max_score=20, stars=self._stars(security_score, 20), rationale=security_rationale, signals=security_signals),
            HealthCategoryRead(name="Maintainability", score=maintainability_score, max_score=15, stars=self._stars(maintainability_score, 15), rationale=maintainability_rationale, signals=maintainability_signals),
            HealthCategoryRead(name="Performance", score=performance_score, max_score=10, stars=self._stars(performance_score, 10), rationale=performance_rationale, signals=performance_signals),
        ]
        overall_score = sum(category.score for category in categories)
        return HealthResponse(repository_id=repository.id, overall_score=overall_score, overall_stars=self._stars(overall_score, 100), categories=categories)

    def architecture_diagram(self, repository_id: int) -> ArchitectureDiagramResponse:
        repository = self.get_repository(repository_id)
        top_level = sorted({Path(file_record.path).parts[0] for file_record in repository.files if Path(file_record.path).parts})
        has_frontend = any(folder in {"frontend", "web", "client"} for folder in top_level)
        diagram = "\n".join([
            "graph TD",
            "  User[User / Browser] --> UI[UI Layer]",
            "  UI --> API[Backend API]",
            "  API --> DB[(SQLAlchemy DB)]",
            "  API --> Vector[(Chroma Vector Store)]",
            "  API --> Redis[(Redis / Celery)]",
            "  API --> LLM[(External LLM API)]",
            "  API --> Git[(Git Provider)]",
        ])
        if has_frontend:
            diagram += "\n  UI --> Frontend[frontend/]"
        explanation = "The diagram shows the user-facing client feeding the FastAPI backend, which coordinates persistence, vector retrieval, async work, and external model/Git integrations."
        return ArchitectureDiagramResponse(repository_id=repository.id, diagram_format="mermaid", diagram_source=diagram, explanation=explanation)

    def onboarding(self, repository_id: int) -> OnboardingResponse:
        repository = self.get_repository(repository_id)
        lessons = [self._architecture_lesson(repository), self._folders_lesson(repository), self._auth_lesson(repository), self._database_lesson(repository), self._api_lesson(repository), self._deployment_lesson(repository)]
        return OnboardingResponse(repository_id=repository.id, lessons=lessons)

    def onboarding_lesson(self, repository_id: int, lesson_slug: str) -> OnboardingLessonResponse:
        lessons = {lesson.slug: lesson for lesson in self.onboarding(repository_id).lessons}
        lesson = lessons.get(lesson_slug)
        if lesson is None:
            raise NotFoundError("Lesson not found")
        return OnboardingLessonResponse(repository_id=repository_id, lesson=lesson)

    def download_docs(self, repository_id: int, openapi_schema: dict | None = None) -> bytes:
        return self.docs_zip(repository_id, openapi_schema)

    def _stars(self, score: int, max_score: int) -> float:
        return round((score / max_score) * 5.0, 1) if max_score else 0.0

    def _documentation_score(self, repository: Repository) -> tuple[int, str, list[str]]:
        signals = ["README detected" if any(file_record.path.lower() == "readme.md" for file_record in repository.files) else "README missing"]
        docs_files = [file_record for file_record in repository.files if file_record.path.lower().startswith(("docs/", "documentation/"))]
        file_summary_count = sum(1 for file_record in repository.files if file_record.summary)
        score = 0
        if signals[0] == "README detected":
            score += 8
        score += min(6, len(docs_files) * 2)
        score += min(6, file_summary_count // 2)
        rationale = f"Documentation signals include {len(docs_files)} docs files and {file_summary_count} file summaries; README presence improves discoverability."
        return score, rationale, signals + [f"docs_files={len(docs_files)}", f"summarized_files={file_summary_count}"]

    def _testing_score(self, repository: Repository) -> tuple[int, str, list[str]]:
        test_files = [file_record.path for file_record in repository.files if any(part in file_record.path.lower() for part in ("test", "tests"))]
        test_deps = [name for name in repository.dependency_analysis.get("dependencies", [])] if repository.dependency_analysis else []
        score = min(10, len(test_files) * 2) + (5 if any("pytest" in str(dep).lower() or "vitest" in str(dep).lower() for dep in test_deps) else 0)
        rationale = f"Testing score is driven by {len(test_files)} test files and whether the dependency graph indicates a test runner."
        return score, rationale, [f"test_files={len(test_files)}", f"test_runner={'yes' if score > len(test_files) * 2 else 'no'}"]

    def _architecture_score(self, repository: Repository) -> tuple[int, str, list[str]]:
        folders = {Path(file_record.path).parts[0] for file_record in repository.files if Path(file_record.path).parts}
        layers = [folder for folder in ("app", "frontend", "alembic", "tests") if folder in folders]
        score = min(20, len(layers) * 4 + (4 if "app" in layers else 0))
        rationale = f"Architecture looks organized around {', '.join(layers) or 'a small flat structure'} with clear separation of concerns."
        return score, rationale, [f"layers={', '.join(layers) or 'none'}"]

    def _security_score(self, repository: Repository) -> tuple[int, str, list[str]]:
        findings = self.intelligence.audit_security(repository.id).findings
        auth_routes = [file_record.path for file_record in repository.files if file_record.path.startswith("app/api/routes/")]
        score = max(0, 20 - min(15, len(findings) * 4))
        if any("auth" in path for path in auth_routes):
            score += 2
        rationale = f"Security score is based on {len(findings)} static findings and whether auth/JWT boundaries are present."
        signals = [f"findings={len(findings)}", f"auth_routes={len(auth_routes)}"]
        return min(score, 20), rationale, signals

    def _maintainability_score(self, repository: Repository) -> tuple[int, str, list[str]]:
        duplicate_risk = len(self.intelligence.detect_bugs(repository.id).findings)
        score = max(0, 15 - min(10, duplicate_risk * 2))
        rationale = f"Maintainability reflects duplicate/weak-code findings and whether the repository has a manageable file count ({repository.file_count})."
        return score, rationale, [f"bug_findings={duplicate_risk}", f"file_count={repository.file_count}"]

    def _performance_score(self, repository: Repository) -> tuple[int, str, list[str]]:
        has_celery = any(name in repository.language_stats for name in ("python",)) and any(file_record.path.startswith("app/tasks/") for file_record in repository.files)
        score = 4 if has_celery else 2
        score += 3 if repository.file_count < 100 else 1
        score += 3 if not self.intelligence.detect_bugs(repository.id).findings else 1
        rationale = "Performance is estimated from async task usage, repository size, and the absence of obvious hot-loop findings."
        return min(score, 10), rationale, [f"async_tasks={'yes' if has_celery else 'no'}", f"file_count={repository.file_count}"]

    def _readme(self, repository: Repository, overview) -> str:
        return f"""# {overview.project_name or repository.name or 'Repository'}

{overview.purpose or 'Repository overview not available.'}

## Architecture

{overview.architecture_summary or 'Architecture summary unavailable.'}

## Key Dependencies

{', '.join(overview.dependencies) or 'No dependencies detected.'}

## Folder Map

{chr(10).join(f'- {folder}: {summary}' for folder, summary in overview.folder_explanations.items())}
"""

    def _architecture_markdown(self, repository: Repository, diagram_source: str) -> str:
        return f"## Architecture Diagram\n\n```mermaid\n{diagram_source}\n```\n"

    def _api_markdown(self, repository: Repository, openapi_schema: dict | None) -> str:
        if not openapi_schema:
            return "API schema unavailable."
        lines = ["# API Reference", ""]
        for path, methods in openapi_schema.get("paths", {}).items():
            for method, spec in methods.items():
                lines.append(f"- `{method.upper()} {path}`: {spec.get('summary') or spec.get('operationId') or 'No summary'}")
        return "\n".join(lines)

    def _developer_guide(self, repository: Repository, overview) -> str:
        return f"# Developer Guide\n\n- Start with the overview: {overview.purpose or 'N/A'}\n- Use the API routes in app/api/routes\n- Keep DB work in repositories and services.\n"

    def _installation_guide(self, repository: Repository) -> str:
        return "# Installation Guide\n\n1. Create a virtualenv.\n2. Install dependencies.\n3. Run Alembic migrations.\n4. Start the API and worker.\n"

    def _contribution_guide(self, repository: Repository) -> str:
        return "# Contribution Guide\n\n- Keep changes small and tested.\n- Update docs when APIs change.\n- Prefer repository/service abstractions.\n"

    def _architecture_lesson(self, repository: Repository) -> OnboardingLessonRead:
        return OnboardingLessonRead(
            slug="architecture",
            title="Architecture",
            objective="Understand the major layers and how data moves through the system.",
            summary="The repository is organized around API routes, service orchestration, persistence, and async tasks.",
            file_refs=["app/factory.py", "app/api/routes/intelligence.py", "app/services/intelligence.py", "app/services/delivery.py"],
            checkpoint_question="Which module assembles the FastAPI application and registers routers?",
            checkpoint_hint="Look at app/factory.py.",
        )

    def _folders_lesson(self, repository: Repository) -> OnboardingLessonRead:
        return OnboardingLessonRead(
            slug="folder-structure",
            title="Folder Structure",
            objective="Learn what each top-level folder is responsible for.",
            summary="app holds backend code, alembic stores migrations, tests covers validation, and frontend hosts the Next.js UI.",
            file_refs=["README.md", "app/models/__init__.py", "app/repositories/__init__.py", "frontend/app/page.tsx"],
            checkpoint_question="Where are the persistence models and repository abstractions located?",
            checkpoint_hint="Inspect app/models and app/repositories.",
        )

    def _auth_lesson(self, repository: Repository) -> OnboardingLessonRead:
        return OnboardingLessonRead(
            slug="auth",
            title="Authentication",
            objective="Understand registration, login, JWT issuance, and protected route guards.",
            summary="Auth uses bcrypt hashing, JWTs, and FastAPI dependencies for protected routes.",
            file_refs=["app/api/routes/auth.py", "app/core/security.py", "app/api/deps.py"],
            checkpoint_question="Which dependency validates the bearer token on protected endpoints?",
            checkpoint_hint="Look for get_current_user in app/api/deps.py.",
        )

    def _database_lesson(self, repository: Repository) -> OnboardingLessonRead:
        return OnboardingLessonRead(
            slug="database",
            title="Database",
            objective="See how the ORM models, session factory, and migrations fit together.",
            summary="SQLAlchemy models define the schema and Alembic tracks versioned changes.",
            file_refs=["app/db/session.py", "app/models/repository.py", "alembic/versions/0001_initial.py", "alembic/versions/0002_intelligence_layer.py"],
            checkpoint_question="Where is the database engine created and how is it configured for SQLite vs PostgreSQL?",
            checkpoint_hint="Read app/db/session.py.",
        )

    def _api_lesson(self, repository: Repository) -> OnboardingLessonRead:
        return OnboardingLessonRead(
            slug="api",
            title="API",
            objective="Map the main REST endpoints to the service layer.",
            summary="Routes orchestrate repository ingestion, chat/search, overview, docs, health, and onboarding flows.",
            file_refs=["app/api/routes/repositories.py", "app/api/routes/intelligence.py", "app/schemas/intelligence.py"],
            checkpoint_question="Which endpoint streams cited chat responses?",
            checkpoint_hint="Search for /repos/{repository_id}/chat.",
        )

    def _deployment_lesson(self, repository: Repository) -> OnboardingLessonRead:
        return OnboardingLessonRead(
            slug="deployment",
            title="Deployment",
            objective="Understand how to run the backend, worker, database, vector store, and UI together.",
            summary="Docker Compose wires the API, Celery worker, Redis, PostgreSQL, Chroma, and frontend containers.",
            file_refs=["Dockerfile", "docker-compose.yml", "frontend/Dockerfile", "Makefile", "scripts/seed_demo.py"],
            checkpoint_question="What service stores vectors persistently during local and production runs?",
            checkpoint_hint="Look for the Chroma service in docker-compose.yml.",
        )

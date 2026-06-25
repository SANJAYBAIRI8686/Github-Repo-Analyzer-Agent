from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
import ast
import json
import re
import tomllib
from typing import Any, Iterable

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import NotFoundError
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.file_record import FileRecord
from app.models.repository import Repository
from app.rag.llm import load_prompt_template, render_prompt, select_llm_provider
from app.rag.retrieval import RetrievalFilters, RepositoryRetrievalEngine, SearchHit
from app.rag.truncation import PromptBudget
from app.repositories.chat_message_repository import ChatMessageRepository
from app.repositories.chat_session_repository import ChatSessionRepository
from app.repositories.file_repository import FileRepository
from app.repositories.repository_repository import RepositoryRepo
from app.schemas.intelligence import (
    AnalysisResponse,
    ChatCitation,
    ChatMessageRead,
    ChatSessionCreateRequest,
    ChatSessionRead,
    DependencyRead,
    DependencyResponse,
    ExplainRequest,
    ExplainResponse,
    FileSummaryResponse,
    FindingRead,
    OverviewResponse,
    SearchHitRead,
    SearchResponse,
)
from app.services.vector_store import ChromaVectorStore, RetrievedChunk


SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{8,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)openai[_-]?api[_-]?key"),
]

SQL_INJECTION_PATTERNS = [
    re.compile(r"execute\(f['\"]"),
    re.compile(r"execute\([^\)]*format\("),
    re.compile(r"text\(f['\"]"),
]

ROUTE_DECORATOR_PATTERN = re.compile(r"@(?:\w+\.)?router\.(?:get|post|put|patch|delete)\(")


@dataclass(slots=True)
class CodeLocation:
    file_path: str
    start_line: int | None = None
    end_line: int | None = None


def _safe_join_lines(chunks: list[RetrievedChunk]) -> str:
    ordered = sorted(chunks, key=lambda item: (item.metadata.get("start_line") or 0, item.metadata.get("end_line") or 0))
    return "\n".join(chunk.text for chunk in ordered)


def _root_name(path: str) -> str:
    parts = Path(path).parts
    if len(parts) > 1:
        return parts[0]
    return path


def _best_language(language_stats: dict[str, Any]) -> str | None:
    if not language_stats:
        return None
    return max(language_stats.items(), key=lambda item: item[1])[0]


def _framework_from_dependencies(dependency_names: Iterable[str]) -> str | None:
    names = {name.lower() for name in dependency_names}
    for framework, markers in {
        "FastAPI": {"fastapi", "uvicorn", "starlette"},
        "Django": {"django", "djangorestframework"},
        "Flask": {"flask", "werkzeug"},
        "React": {"react", "react-dom"},
        "Next.js": {"next", "nextjs"},
        "Celery": {"celery"},
    }.items():
        if names & markers:
            return framework
    return None


class DependencyParser:
    def parse_text(self, content: str, source_file: str) -> list[DependencyRead]:
        if source_file.endswith("requirements.txt"):
            return self._parse_requirements(content, source_file)
        if source_file.endswith("pyproject.toml"):
            return self._parse_pyproject(content, source_file)
        if source_file.endswith("package.json"):
            return self._parse_package_json(content, source_file)
        return []

    def _parse_requirements(self, content: str, source_file: str) -> list[DependencyRead]:
        dependencies: list[DependencyRead] = []
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            name = re.split(r"[<>=!~\[]", stripped, maxsplit=1)[0].strip()
            dependencies.append(
                DependencyRead(
                    name=name,
                    spec=stripped[len(name) :].strip() or None,
                    description=self.describe_dependency(name),
                    why_used=self.why_used(name, source_file),
                    source_file=source_file,
                )
            )
        return dependencies

    def _parse_pyproject(self, content: str, source_file: str) -> list[DependencyRead]:
        dependencies: list[DependencyRead] = []
        data = tomllib.loads(content)
        project = data.get("project", {})
        for item in project.get("dependencies", []) or []:
            name = re.split(r"[<>=!~\[]", item, maxsplit=1)[0].strip()
            dependencies.append(
                DependencyRead(
                    name=name,
                    spec=item[len(name) :].strip() or None,
                    description=self.describe_dependency(name),
                    why_used=self.why_used(name, source_file),
                    source_file=source_file,
                )
            )
        optional = project.get("optional-dependencies", {}) or {}
        for extra_deps in optional.values():
            for item in extra_deps or []:
                name = re.split(r"[<>=!~\[]", item, maxsplit=1)[0].strip()
                dependencies.append(
                    DependencyRead(
                        name=name,
                        spec=item[len(name) :].strip() or None,
                        description=self.describe_dependency(name),
                        why_used=self.why_used(name, source_file),
                        source_file=source_file,
                    )
                )
        return self._dedupe(dependencies)

    def _parse_package_json(self, content: str, source_file: str) -> list[DependencyRead]:
        dependencies: list[DependencyRead] = []
        data = json.loads(content)
        for group_name in ("dependencies", "devDependencies"):
            for name, spec in (data.get(group_name) or {}).items():
                dependencies.append(
                    DependencyRead(
                        name=name,
                        spec=str(spec),
                        description=self.describe_dependency(name),
                        why_used=self.why_used(name, source_file),
                        source_file=source_file,
                    )
                )
        return self._dedupe(dependencies)

    def describe_dependency(self, name: str) -> str:
        descriptions = {
            "fastapi": "Modern Python web framework for APIs.",
            "sqlalchemy": "Database ORM and SQL toolkit.",
            "alembic": "Database migration tool.",
            "celery": "Distributed task queue for background work.",
            "redis": "In-memory broker/cache often used by Celery.",
            "chromadb": "Persistent vector store for semantic retrieval.",
            "gitpython": "Python bindings for Git operations.",
            "python-jose": "JWT token creation and verification.",
            "passlib": "Password hashing and verification.",
            "pydantic": "Data validation and schema definition.",
            "uvicorn": "ASGI server for FastAPI applications.",
        }
        return descriptions.get(name.lower(), "Third-party package used by the application.")

    def why_used(self, name: str, source_file: str) -> str:
        lower = name.lower()
        if lower in {"fastapi", "uvicorn"}:
            return "Used to serve the API layer and run the app."
        if lower in {"sqlalchemy", "alembic"}:
            return "Used for persistence models and schema migrations."
        if lower in {"celery", "redis"}:
            return "Used for background processing and task coordination."
        if lower in {"chromadb", "openai"}:
            return "Used for vector storage or embeddings/LLM access."
        if lower in {"gitpython"}:
            return "Used to clone and inspect Git repositories."
        if source_file.endswith("package.json"):
            return "Used by the frontend/runtime declared in package.json."
        return f"Declared in {source_file} for runtime or development support."

    def _dedupe(self, dependencies: list[DependencyRead]) -> list[DependencyRead]:
        unique: dict[tuple[str, str | None], DependencyRead] = {}
        for dependency in dependencies:
            unique[(dependency.name.lower(), dependency.spec)] = dependency
        return list(unique.values())


class RepositoryIntelligenceService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.vector_store = ChromaVectorStore(settings.chroma_persist_dir)
        self.retrieval = RepositoryRetrievalEngine(self.vector_store, settings)
        self.llm = select_llm_provider(settings)
        self.budget = PromptBudget(settings.prompt_max_context_chars)
        self.repo_repo = RepositoryRepo(session)
        self.file_repo = FileRepository(session)
        self.chat_sessions = ChatSessionRepository(session)
        self.chat_messages = ChatMessageRepository(session)
        self.dependency_parser = DependencyParser()

    def get_repository(self, repository_id: int) -> Repository:
        repository = self.repo_repo.get_by_id(repository_id)
        if repository is None:
            raise NotFoundError("Repository not found")
        return repository

    def search(self, repository_id: int, query: str, *, file_path: str | None = None, language: str | None = None, symbol_name: str | None = None, top_k: int | None = None) -> SearchResponse:
        filters = RetrievalFilters(file_path=file_path, language=language, symbol_name=symbol_name)
        hits = self.retrieval.search(repository_id, query, top_k=top_k or self.settings.search_top_k, filters=filters)
        return SearchResponse(
            repository_id=repository_id,
            query=query,
            hits=[
                SearchHitRead(
                    chunk_id=hit.chunk_id,
                    file_path=hit.file_path,
                    language=hit.language,
                    symbol_name=hit.symbol_name,
                    start_line=hit.start_line,
                    end_line=hit.end_line,
                    snippet=hit.snippet,
                    score=hit.score,
                    citation=hit.citation,
                )
                for hit in hits
            ],
        )

    def build_chat_stream(self, repository_id: int, user_id: int | None, message: str, *, session_id: int | None = None, file_path: str | None = None, language: str | None = None, symbol_name: str | None = None) -> tuple[ChatSession, list[ChatCitation], Any]:
        repository = self.get_repository(repository_id)
        if session_id is None:
            chat_session = self.chat_sessions.create(repository_id=repository.id, user_id=user_id)
        else:
            chat_session = self.chat_sessions.get_by_id(session_id)
            if chat_session is None or chat_session.repository_id != repository.id:
                raise NotFoundError("Chat session not found")

        self.chat_messages.create(chat_session_id=chat_session.id, role="user", content=message, citations=None)
        self.session.commit()

        filters = RetrievalFilters(file_path=file_path, language=language, symbol_name=symbol_name)
        chunks = self.retrieval.retrieve(repository.id, message, filters=filters)
        if not chunks:
            raise NotFoundError("not found in repo")

        citations = [
            ChatCitation(
                file_path=str(chunk.metadata.get("file_path", "unknown")),
                line_start=chunk.metadata.get("start_line"),
                line_end=chunk.metadata.get("end_line"),
                symbol_name=chunk.metadata.get("symbol_name"),
            )
            for chunk in chunks
        ]
        history = self.chat_messages.list_recent(chat_session.id, self.settings.memory_window_messages)
        history_text = self._format_history(history)
        context_text = "\n\n".join(self.retrieval.context_snippets(chunks))
        prompt = render_prompt(
            "chat_system.txt",
            context=context_text,
            history=history_text,
            question=message,
            citations="\n".join(f"- {citation.file_path}:{citation.line_start}-{citation.line_end}" for citation in citations),
        )

        def stream() -> Any:
            answer_parts: list[str] = []
            try:
                for part in self.llm.stream(prompt, system_prompt=load_prompt_template("chat_system.txt"), max_tokens=self.settings.llm_max_output_tokens):
                    answer_parts.append(part)
                    yield part
                citation_block = "\n\nSources:\n" + "\n".join(
                    f"- {citation.file_path}:{citation.line_start}-{citation.line_end}" for citation in citations
                )
                yield citation_block
                self.chat_messages.create(
                    chat_session_id=chat_session.id,
                    role="assistant",
                    content="".join(answer_parts) + citation_block,
                    citations=[citation.model_dump() for citation in citations],
                )
                self.session.commit()
            except Exception as exc:
                self.session.rollback()
                raise exc

        return chat_session, citations, stream()

    def create_chat_session(self, repository_id: int, user_id: int | None, title: str | None = None) -> ChatSessionRead:
        repository = self.get_repository(repository_id)
        chat_session = self.chat_sessions.create(repository_id=repository.id, user_id=user_id, title=title)
        self.session.commit()
        return ChatSessionRead.model_validate(chat_session)

    def list_chat_sessions(self, repository_id: int) -> list[ChatSessionRead]:
        repository = self.get_repository(repository_id)
        return [ChatSessionRead.model_validate(chat_session) for chat_session in self.chat_sessions.list_by_repository(repository.id)]

    def list_chat_history(self, repository_id: int, session_id: int) -> list[ChatMessageRead]:
        repository = self.get_repository(repository_id)
        chat_session = self.chat_sessions.get_by_id(session_id)
        if chat_session is None or chat_session.repository_id != repository.id:
            raise NotFoundError("Chat session not found")
        messages = list(reversed(self.chat_messages.list_recent(chat_session.id, 10_000)))
        return [ChatMessageRead.model_validate(message) for message in messages]

    def _format_history(self, messages: list[ChatMessage]) -> str:
        ordered = list(reversed(messages))
        lines = [f"{message.role}: {message.content}" for message in ordered]
        return "\n".join(lines)

    def build_overview(self, repository_id: int) -> OverviewResponse:
        repository = self.get_repository(repository_id)
        dependencies = self.analyze_dependencies(repository_id).dependencies
        dependency_names = [dependency.name for dependency in dependencies]
        main_language = _best_language(repository.language_stats)
        framework = _framework_from_dependencies(dependency_names)
        folder_explanations = self._folder_explanations(repository)
        architecture_summary = self._architecture_summary(repository, dependency_names, folder_explanations, framework)
        complexity, learning_difficulty = self._difficulty_from_repo(repository, dependency_names)
        purpose = self._purpose_from_repo(repository, framework, main_language, folder_explanations)
        overview = OverviewResponse(
            repository_id=repository.id,
            project_name=repository.name or Path(repository.url.rstrip("/")).name,
            purpose=purpose,
            main_language=main_language,
            framework=framework,
            file_count=repository.file_count,
            dependencies=dependency_names,
            architecture_summary=architecture_summary,
            complexity=complexity,
            learning_difficulty=learning_difficulty,
            folder_explanations=folder_explanations,
        )
        repository.overview = overview.model_dump()
        repository.architecture_summary = architecture_summary
        repository.complexity = complexity
        repository.learning_difficulty = learning_difficulty
        repository.dependency_analysis = {"dependencies": [dependency.model_dump() for dependency in dependencies]}
        self.session.commit()
        return overview

    def summarize_file(self, repository_id: int, file_path: str) -> FileSummaryResponse:
        repository = self.get_repository(repository_id)
        file_record = self.file_repo.get_by_repo_and_path(repository.id, file_path)
        if file_record is None:
            raise NotFoundError("File not found")
        chunks = self.retrieval.fetch_by_path(repository.id, file_path)
        if not chunks:
            raise NotFoundError("File content not found")
        summary = self._summarize_text(file_path, _safe_join_lines(chunks))
        file_record.summary = summary
        self.session.commit()
        return FileSummaryResponse(repository_id=repository.id, file_path=file_path, summary=summary)

    def analyze_dependencies(self, repository_id: int) -> DependencyResponse:
        repository = self.get_repository(repository_id)
        dependency_files = ["requirements.txt", "pyproject.toml", "package.json"]
        dependencies: list[DependencyRead] = []
        seen_files: set[str] = set()
        for dependency_file in dependency_files:
            chunks = self.retrieval.fetch_by_path(repository.id, dependency_file)
            if not chunks:
                continue
            content = _safe_join_lines(chunks)
            if dependency_file in seen_files:
                continue
            seen_files.add(dependency_file)
            dependencies.extend(self.dependency_parser.parse_text(content, dependency_file))
        dependencies = self._enrich_dependency_why(repository, dependencies)
        repository.dependency_analysis = {"dependencies": [dependency.model_dump() for dependency in dependencies]}
        self.session.commit()
        return DependencyResponse(repository_id=repository.id, dependencies=dependencies)

    def explain(self, request: ExplainRequest) -> ExplainResponse:
        code = request.code
        citations: list[str] = []
        if code is None:
            if request.repo_id is None or not request.symbol_name and not request.file_path:
                raise HTTPException(status_code=400, detail="Provide either code or a repository reference")
            repository = self.get_repository(request.repo_id)
            filters = RetrievalFilters(file_path=request.file_path, symbol_name=request.symbol_name, language=request.language)
            chunks = self.retrieval.retrieve(repository.id, request.symbol_name or request.file_path or "explain", filters=filters, top_k=3)
            if not chunks:
                raise NotFoundError("not found in repo")
            code = _safe_join_lines(chunks)
            citations = self.retrieval.citation_lines(chunks)
        explanation = self._explain_code(code, request.language)
        explanation.citations = citations
        return explanation

    def detect_bugs(self, repository_id: int) -> AnalysisResponse:
        repository = self.get_repository(repository_id)
        findings = self._find_bug_findings(repository)
        return AnalysisResponse(repository_id=repository.id, findings=findings)

    def audit_security(self, repository_id: int) -> AnalysisResponse:
        repository = self.get_repository(repository_id)
        findings = self._find_security_findings(repository)
        return AnalysisResponse(repository_id=repository.id, findings=findings)

    def file_summary_or_create(self, repository_id: int, file_path: str) -> FileSummaryResponse:
        file_record = self.file_repo.get_by_repo_and_path(repository_id, file_path)
        if file_record and file_record.summary:
            return FileSummaryResponse(repository_id=repository_id, file_path=file_path, summary=file_record.summary)
        return self.summarize_file(repository_id, file_path)

    def _summarize_text(self, file_path: str, content: str) -> str:
        prompt = render_prompt("overview_system.txt", content=content, file_path=file_path)
        return self.llm.complete(prompt, system_prompt=load_prompt_template("overview_system.txt"), max_tokens=self.settings.llm_max_output_tokens)

    def _purpose_from_repo(self, repository: Repository, framework: str | None, main_language: str | None, folder_explanations: dict[str, str]) -> str:
        if framework:
            return f"This repository appears to be a {framework} application."
        if main_language:
            return f"This repository is primarily a {main_language} codebase."
        if folder_explanations:
            return f"This repository is organized around {', '.join(list(folder_explanations)[:3])}."
        return f"Repository {repository.name or repository.url} does not have enough context for a stronger purpose statement."

    def _architecture_summary(self, repository: Repository, dependency_names: list[str], folder_explanations: dict[str, str], framework: str | None) -> str:
        folder_bits = "; ".join(f"{name}: {summary}" for name, summary in list(folder_explanations.items())[:5])
        dependency_bits = ", ".join(dependency_names[:8]) or "no declared dependencies found"
        framework_text = framework or "no obvious framework detected"
        return (
            f"{repository.file_count} tracked files, {len(dependency_names)} dependencies, {framework_text}. "
            f"Top-level folders: {folder_bits or 'not enough structure detected'}. "
            f"Key dependencies: {dependency_bits}."
        )

    def _difficulty_from_repo(self, repository: Repository, dependency_names: list[str]) -> tuple[str, str]:
        score = repository.file_count + len(dependency_names) * 2 + len(repository.language_stats)
        if score < 20:
            return "low", "easy"
        if score < 80:
            return "medium", "moderate"
        return "high", "hard"

    def _folder_explanations(self, repository: Repository) -> dict[str, str]:
        folders: dict[str, list[str]] = defaultdict(list)
        for file_record in repository.files:
            folders[_root_name(file_record.path)].append(file_record.path)
        explanations: dict[str, str] = {}
        for folder, paths in sorted(folders.items()):
            if folder in {"app", "src"}:
                explanations[folder] = "Primary application code and runtime wiring."
            elif folder in {"tests", "test"}:
                explanations[folder] = "Automated tests and verification coverage."
            elif folder in {"docs", "documentation"}:
                explanations[folder] = "Documentation and reference material."
            elif folder in {"alembic", "migrations"}:
                explanations[folder] = "Database schema migrations."
            else:
                explanations[folder] = f"Contains {len(paths)} tracked file(s) related to this area."
        return explanations

    def _enrich_dependency_why(self, repository: Repository, dependencies: list[DependencyRead]) -> list[DependencyRead]:
        framework = _framework_from_dependencies([dependency.name for dependency in dependencies])
        for dependency in dependencies:
            if framework and framework.lower() in dependency.name.lower():
                dependency.why_used = f"Supports the repo's {framework} stack."
        return dependencies

    def _explain_code(self, code: str, language: str | None) -> ExplainResponse:
        inputs: list[str] = []
        outputs: list[str] = []
        improvements: list[str] = []
        complexity = "O(1)"
        try:
            tree = ast.parse(code)
            function_nodes = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
            class_nodes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            if function_nodes:
                node = function_nodes[0]
                inputs = [arg.arg for arg in node.args.args]
                if node.args.vararg:
                    inputs.append(f"*{node.args.vararg.arg}")
                if node.args.kwarg:
                    inputs.append(f"**{node.args.kwarg.arg}")
            outputs = ["Return value if the function returns explicitly."]
            if class_nodes and not function_nodes:
                outputs = ["Instances or behaviors exposed by the class."]
            loop_count = sum(isinstance(node, (ast.For, ast.While)) for node in ast.walk(tree))
            branch_count = sum(isinstance(node, (ast.If, ast.Try, ast.BoolOp)) for node in ast.walk(tree))
            if loop_count > 1:
                complexity = "O(n^2) or worse depending on nested loops"
            elif loop_count == 1:
                complexity = "O(n)"
            elif branch_count:
                complexity = "O(branches)"
            improvements = self._code_improvements(tree)
        except SyntaxError:
            improvements = ["Fix syntax issues before analysis."]
        prompt = render_prompt("explain_system.txt", code=code, language=language or "unknown")
        purpose = self.llm.complete(prompt, system_prompt=load_prompt_template("explain_system.txt"), max_tokens=self.settings.llm_max_output_tokens)
        if not purpose.strip():
            purpose = "This code implements the provided behavior using the visible control flow and data handling."
        return ExplainResponse(
            purpose=purpose,
            inputs=inputs,
            outputs=outputs,
            complexity=complexity,
            improvements=improvements or ["No obvious improvement detected from static analysis."],
            citations=[],
        )

    def _code_improvements(self, tree: ast.AST) -> list[str]:
        improvements: list[str] = []
        if any(isinstance(node, ast.ExceptHandler) and node.type is None for node in ast.walk(tree)):
            improvements.append("Replace bare except blocks with explicit exception types.")
        if sum(isinstance(node, ast.For) for node in ast.walk(tree)) > 1:
            improvements.append("Review nested loops for algorithmic simplification.")
        if any(isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and node.value.value is None for node in ast.walk(tree)):
            improvements.append("Consider validating inputs before assigning sentinel values.")
        return improvements

    def _find_bug_findings(self, repository: Repository) -> list[FindingRead]:
        findings: list[FindingRead] = []
        python_files = [file_record for file_record in repository.files if file_record.language == "python"]
        function_bodies: dict[str, tuple[str, str, int | None]] = {}
        for file_record in python_files:
            content = _safe_join_lines(self.retrieval.fetch_by_path(repository.id, file_record.path))
            if not content:
                continue
            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue
            lines = content.splitlines()
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    start = getattr(node, "lineno", None)
                    end = getattr(node, "end_lineno", start)
                    snippet = "\n".join(lines[start - 1 : end]) if start and end else ""
                    normalized = re.sub(r"\s+", " ", snippet).strip()
                    signature = f"{file_record.path}:{node.name}"
                    if normalized in function_bodies:
                        other_file, other_name, other_line = function_bodies[normalized]
                        findings.append(
                            FindingRead(
                                severity="medium",
                                title="Duplicated code",
                                details=f"Function body duplicates {other_file}:{other_name}.",
                                file_path=file_record.path,
                                line=start,
                                kind="bug",
                            )
                        )
                    else:
                        function_bodies[normalized] = (file_record.path, node.name, start)
                    findings.extend(self._unused_and_unreachable_findings(file_record.path, node, snippet, start))
        return self._dedupe_findings(findings)

    def _unused_and_unreachable_findings(self, file_path: str, node: ast.FunctionDef | ast.AsyncFunctionDef, snippet: str, start_line: int | None) -> list[FindingRead]:
        findings: list[FindingRead] = []
        assigned: set[str] = set()
        loaded: set[str] = set()
        unreachable_line: int | None = None
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                if isinstance(child.ctx, ast.Store):
                    assigned.add(child.id)
                elif isinstance(child.ctx, ast.Load):
                    loaded.add(child.id)
            if isinstance(child, ast.ExceptHandler) and child.type is None:
                findings.append(
                    FindingRead(
                        severity="medium",
                        title="Weak exception handling",
                        details="Bare except swallows all exceptions and obscures failures.",
                        file_path=file_path,
                        line=getattr(child, "lineno", start_line),
                        kind="bug",
                    )
                )
        for statement in getattr(node, "body", []):
            if unreachable_line is not None:
                findings.append(
                    FindingRead(
                        severity="low",
                        title="Unreachable code",
                        details="Statement appears after a terminating control-flow instruction.",
                        file_path=file_path,
                        line=getattr(statement, "lineno", start_line),
                        kind="bug",
                    )
                )
                continue
            if isinstance(statement, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                unreachable_line = getattr(statement, "lineno", start_line)
        unused = sorted(name for name in assigned - loaded if not name.startswith("_") )
        if unused:
            findings.append(
                FindingRead(
                    severity="low",
                    title="Unused variable",
                    details=f"Unused local(s): {', '.join(unused[:5])}.",
                    file_path=file_path,
                    line=start_line,
                    kind="bug",
                )
            )
        return findings

    def _find_security_findings(self, repository: Repository) -> list[FindingRead]:
        findings: list[FindingRead] = []
        for file_record in repository.files:
            content = _safe_join_lines(self.retrieval.fetch_by_path(repository.id, file_record.path))
            if not content:
                continue
            lines = content.splitlines()
            for line_index, line in enumerate(lines, start=1):
                for pattern in SECRET_PATTERNS:
                    if pattern.search(line):
                        findings.append(
                            FindingRead(
                                severity="critical",
                                title="Potential hardcoded secret",
                                details="Secret-like value or credential pattern detected statically.",
                                file_path=file_record.path,
                                line=line_index,
                                kind="security",
                            )
                        )
                for pattern in SQL_INJECTION_PATTERNS:
                    if pattern.search(line):
                        findings.append(
                            FindingRead(
                                severity="high",
                                title="Potential SQL injection risk",
                                details="Raw SQL string interpolation detected in an execution path.",
                                file_path=file_record.path,
                                line=line_index,
                                kind="security",
                            )
                        )
            if file_record.path.startswith("app/api/routes/") and self._route_without_auth(content) and not any(part in file_record.path for part in ("auth", "health")):
                findings.append(
                    FindingRead(
                        severity="medium",
                        title="Route without explicit auth dependency",
                        details="Route appears to be missing a protected-route guard or get_current_user dependency.",
                        file_path=file_record.path,
                        line=1,
                        kind="security",
                    )
                )
        if self._weak_jwt_config(repository):
            findings.append(
                FindingRead(
                    severity="high",
                    title="Weak JWT configuration",
                    details="JWT secret or signing configuration appears weak or defaulted.",
                    file_path="app/core/config.py",
                    line=1,
                    kind="security",
                )
            )
        return self._dedupe_findings(findings)

    def _route_without_auth(self, content: str) -> bool:
        if not ROUTE_DECORATOR_PATTERN.search(content):
            return False
        return "get_current_user" not in content and "Depends(get_current_user)" not in content

    def _weak_jwt_config(self, repository: Repository) -> bool:
        config_content = _safe_join_lines(self.retrieval.fetch_by_path(repository.id, "app/core/config.py"))
        return "change-me" in config_content or "SECRET_KEY" in config_content and "must be set" in config_content

    def _dedupe_findings(self, findings: list[FindingRead]) -> list[FindingRead]:
        unique: dict[tuple[str, str | None, int | None, str], FindingRead] = {}
        for finding in findings:
            unique[(finding.title, finding.file_path, finding.line, finding.kind)] = finding
        return list(unique.values())

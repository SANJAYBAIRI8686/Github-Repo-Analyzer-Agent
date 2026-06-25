from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.factory import create_app
from app.models.file_record import FileRecord
from app.models.repository import Repository
from app.repositories.repository_repository import RepositoryRepo
from app.rag.retrieval import RetrievalFilters, RepositoryRetrievalEngine
from app.schemas.intelligence import ExplainRequest
from app.services.embedding_provider import OpenAIEmbeddingProvider
from app.services.intelligence import DependencyParser, RepositoryIntelligenceService, SECRET_PATTERNS
from app.services.vector_store import ChromaVectorStore, RetrievedChunk


AUTH_CODE = """
from fastapi import APIRouter

router = APIRouter()

@router.post('/login')
def login(email: str, password: str):
    if password != 'secret':
        raise ValueError('bad credentials')
    return {'token': 'jwt'}
""".strip()


MAIN_CODE = """
from app.api.routes.auth import router

def create_app():
    return router
""".strip()


REQS = """
fastapi>=0.115.0
sqlalchemy>=2.0.0
chromadb>=0.5.0
""".strip()


class FakeVectorStore:
    def __init__(self) -> None:
        self.last_filters = None

    def query_chunks(self, repository_id: int, query_embedding: list[float], *, limit: int, metadata_filters: dict[str, object] | None = None):
        self.last_filters = metadata_filters
        return [
            RetrievedChunk(
                chunk_id="1",
                text=AUTH_CODE,
                metadata={
                    "repo_id": repository_id,
                    "file_path": "app/api/routes/auth.py",
                    "language": "python",
                    "symbol_name": "login",
                    "start_line": 1,
                    "end_line": 9,
                },
                distance=0.2,
            )
        ]

    def fetch_chunks(self, repository_id: int, *, metadata_filters: dict[str, object] | None = None):
        self.last_filters = metadata_filters
        return [
            RetrievedChunk(
                chunk_id="1",
                text=AUTH_CODE,
                metadata={
                    "repo_id": repository_id,
                    "file_path": "app/api/routes/auth.py",
                    "language": "python",
                    "symbol_name": "login",
                    "start_line": 1,
                    "end_line": 9,
                },
            )
        ]

    def upsert_chunks(self, repository_id: int, chunks: list[dict[str, object]], embeddings: list[list[float]]) -> None:
        return None


class FakeLLM:
    def complete(self, prompt: str, *, system_prompt: str | None = None, max_tokens: int | None = None) -> str:
        if "explain" in (system_prompt or "").lower():
            return "It validates credentials and issues a token."
        return "This repo exposes login and application wiring."

    def stream(self, prompt: str, *, system_prompt: str | None = None, max_tokens: int | None = None):
        yield "Login verifies the password and returns a JWT."


def _seed_repo(settings) -> int:
    session = get_session_factory(settings)()
    try:
        repo = RepositoryRepo(session).create(
            user_id=None,
            url="https://github.com/example/demo",
            owner="example",
            name="demo",
            default_branch="main",
            commit_hash="abc123",
            status="completed",
            file_count=3,
            language_stats={"python": 3},
        )
        session.add_all(
            [
                FileRecord(repository_id=repo.id, path="app/api/routes/auth.py", language="python", size=len(AUTH_CODE), hash="h1", summary=None),
                FileRecord(repository_id=repo.id, path="app/main.py", language="python", size=len(MAIN_CODE), hash="h2", summary=None),
                FileRecord(repository_id=repo.id, path="requirements.txt", language="text", size=len(REQS), hash="h3", summary=None),
            ]
        )
        session.commit()

        store = ChromaVectorStore(settings.chroma_persist_dir)
        embedder = OpenAIEmbeddingProvider(settings.openai_api_key, settings.openai_embedding_model)
        texts = [AUTH_CODE, MAIN_CODE, REQS]
        chunks = [
            {
                "id": f"{repo.id}:auth:1",
                "text": AUTH_CODE,
                "metadata": {
                    "repo_id": repo.id,
                    "file_path": "app/api/routes/auth.py",
                    "language": "python",
                    "symbol_name": "login",
                    "start_line": 1,
                    "end_line": 9,
                    "chunk_type": "semantic",
                },
            },
            {
                "id": f"{repo.id}:main:1",
                "text": MAIN_CODE,
                "metadata": {
                    "repo_id": repo.id,
                    "file_path": "app/main.py",
                    "language": "python",
                    "symbol_name": "create_app",
                    "start_line": 1,
                    "end_line": 4,
                    "chunk_type": "semantic",
                },
            },
            {
                "id": f"{repo.id}:reqs:1",
                "text": REQS,
                "metadata": {
                    "repo_id": repo.id,
                    "file_path": "requirements.txt",
                    "language": "text",
                    "symbol_name": None,
                    "start_line": 1,
                    "end_line": 3,
                    "chunk_type": "text",
                },
            },
        ]
        store.upsert_chunks(repo.id, chunks, embedder.embed_texts(texts))
        return repo.id
    finally:
        session.close()


def test_retrieval_filtering_and_citations() -> None:
    settings = get_settings()
    store = FakeVectorStore()
    engine = RepositoryRetrievalEngine(store, settings)
    hits = engine.search(7, "How does login work?", filters=RetrievalFilters(file_path="app/api/routes/auth.py"))
    assert store.last_filters == {"file_path": "app/api/routes/auth.py", "language": None, "symbol_name": None}
    assert hits[0].citation == "app/api/routes/auth.py:1-9"


def test_dependency_parser_parses_requirements() -> None:
    parser = DependencyParser()
    deps = parser.parse_text(REQS, "requirements.txt")
    names = {dep.name for dep in deps}
    assert {"fastapi", "sqlalchemy", "chromadb"}.issubset(names)


def test_secret_pattern_detector_flags_secret_line() -> None:
    line = "OPENAI_API_KEY = 'sk-1234567890abcdef'"
    assert any(pattern.search(line) for pattern in SECRET_PATTERNS)


def test_chat_search_and_overview_api(monkeypatch) -> None:
    monkeypatch.setattr("app.services.intelligence.select_llm_provider", lambda settings: FakeLLM())
    app = create_app()
    settings = app.state.settings
    repo_id = _seed_repo(settings)

    client = TestClient(app)
    register_response = client.post("/auth/register", json={"email": "user@example.com", "password": "Passw0rd!"})
    token = register_response.json()["access_token"]

    overview_response = client.get(f"/repos/{repo_id}/overview", headers={"Authorization": f"Bearer {token}"})
    assert overview_response.status_code == 200
    assert overview_response.json()["main_language"] == "python"
    assert "FastAPI" in overview_response.json()["architecture_summary"]

    search_response = client.post(
        f"/repos/{repo_id}/search",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "How does login work?", "file_path": "app/api/routes/auth.py", "top_k": 3},
    )
    assert search_response.status_code == 200
    hits = search_response.json()["hits"]
    assert hits[0]["file_path"] == "app/api/routes/auth.py"
    assert hits[0]["citation"] == "app/api/routes/auth.py:1-9"

    with client.stream(
        "POST",
        f"/repos/{repo_id}/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "How does login work?", "file_path": "app/api/routes/auth.py"},
    ) as response:
        body = "".join(response.iter_text())
        assert response.status_code == 200
        assert "Login verifies the password" in body
        assert "Sources:" in body
        assert "app/api/routes/auth.py:1-9" in body

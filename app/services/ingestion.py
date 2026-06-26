from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session
from kombu.exceptions import OperationalError

from app.core.config import Settings
from app.core.errors import NotFoundError
from app.models.ingestion_job import IngestionJob
from app.models.repository import Repository
from app.repositories.file_repository import FileRepository
from app.repositories.job_repository import JobRepository
from app.repositories.repository_repository import RepositoryRepo
from app.schemas.repositories import RepositoryIngestRequest
from app.services.chunking import chunk_file
from app.services.embedding_provider import OpenAIEmbeddingProvider
from app.services.file_reader import read_repo_files
from app.services.git_service import GitService
from app.services.vector_store import ChromaVectorStore


@dataclass(slots=True)
class IngestionCoordinator:
    session: Session
    settings: Settings
    git_service: GitService
    embedding_provider: OpenAIEmbeddingProvider
    vector_store: ChromaVectorStore

    @classmethod
    def from_settings(cls, settings: Settings, session: Session) -> "IngestionCoordinator":
        return cls(
            session=session,
            settings=settings,
            git_service=GitService(),
            embedding_provider=OpenAIEmbeddingProvider(settings.openai_api_key, settings.openai_embedding_model),
            vector_store=ChromaVectorStore(settings.chroma_persist_dir),
        )

    def create_job(self, user_id: int, payload: RepositoryIngestRequest) -> tuple[Repository, IngestionJob]:
        repo_repo = RepositoryRepo(self.session)
        job_repo = JobRepository(self.session)
        repository = repo_repo.create(
            user_id=user_id,
            url=payload.url,
            status="queued",
            file_count=0,
            language_stats={},
        )
        job = job_repo.create(repository_id=repository.id, status="queued", progress_pct=0, stage="queued")
        return repository, job

    def enqueue_or_run(self, job_id: int) -> None:
        if self.settings.environment == "production" and self.settings.celery_broker_url.startswith("redis://"):
            from app.tasks.ingestion_tasks import ingest_repository

            try:
                ingest_repository.delay(job_id)
                return
            except (OperationalError, RuntimeError):
                pass
        self.run(job_id)

    def _update_job(self, job: IngestionJob, **changes: Any) -> None:
        JobRepository(self.session).update(job, **changes)
        self.session.commit()

    def run(self, job_id: int) -> None:
        job_repo = JobRepository(self.session)
        repo_repo = RepositoryRepo(self.session)
        file_repo = FileRepository(self.session)
        job = job_repo.get_by_id(job_id)
        if job is None:
            raise NotFoundError("Job not found")
        repository = repo_repo.get_by_id(job.repository_id)
        if repository is None:
            raise NotFoundError("Repository not found")

        clone_result = None
        try:
            self._update_job(job, status="running", stage="cloning", progress_pct=5, error=None)
            clone_result = self.git_service.clone_repository(repository.url, shallow=self.settings.shallow_clone_default)
            repository.commit_hash = clone_result.commit_hash
            repository.default_branch = clone_result.default_branch
            repository.owner = clone_result.repo_owner
            repository.name = clone_result.repo_name

            duplicate = repo_repo.get_by_url_and_commit(repository.url, repository.commit_hash)
            if duplicate and duplicate.id != repository.id:
                repository.status = "completed"
                self._update_job(job, status="completed", stage="duplicate-detected", progress_pct=100)
                self.session.commit()
                return

            self._update_job(job, stage="reading-files", progress_pct=20)
            files = read_repo_files(clone_result.work_dir, self.settings.max_file_size_bytes)
            repository.file_count = len(files)
            language_stats: dict[str, int] = {}
            chunks_payload: list[dict[str, Any]] = []

            for file_index, file_item in enumerate(files, start=1):
                if file_repo.get_by_repo_and_path(repository.id, file_item.path) is None:
                    file_repo.create(
                        repository_id=repository.id,
                        path=file_item.path,
                        language=file_item.language,
                        size=file_item.size,
                        hash=file_item.hash,
                        summary=None,
                    )
                if file_item.language:
                    language_stats[file_item.language] = language_stats.get(file_item.language, 0) + 1
                for chunk_index, chunk in enumerate(chunk_file(file_item.content, file_item.path, file_item.language)):
                    chunk_id = f"{repository.id}:{file_item.path}:{chunk.metadata.get('start_line')}:{chunk.metadata.get('end_line')}:{chunk_index}"
                    chunks_payload.append(
                        {
                            "id": chunk_id,
                            "text": chunk.text,
                            "metadata": {"repo_id": repository.id, **chunk.metadata},
                        }
                    )
                progress = 20 + int((file_index / max(len(files), 1)) * 50)
                self._update_job(job, stage="parsing-chunking", progress_pct=min(progress, 70))

            repository.language_stats = language_stats
            repository.status = "indexing"
            self.session.commit()

            if chunks_payload:
                self._update_job(job, stage="embedding", progress_pct=80)
                embeddings = self.embedding_provider.embed_texts([item["text"] for item in chunks_payload])
                self.vector_store.upsert_chunks(repository.id, chunks_payload, embeddings)

            repository.status = "completed"
            self._update_job(job, status="completed", stage="finished", progress_pct=100)
            self.session.commit()
        except Exception as exc:
            repository.status = "failed"
            self._update_job(job, status="failed", stage="failed", progress_pct=100, error=str(exc))
            self.session.commit()
            raise
        finally:
            if clone_result is not None:
                self.git_service.cleanup(clone_result.work_dir)
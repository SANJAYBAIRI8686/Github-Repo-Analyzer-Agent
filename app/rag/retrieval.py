from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings
from app.services.embedding_provider import OpenAIEmbeddingProvider
from app.services.vector_store import RetrievedChunk, VectorStore


@dataclass(slots=True)
class RetrievalFilters:
    file_path: str | None = None
    language: str | None = None
    symbol_name: str | None = None


@dataclass(slots=True)
class SearchHit:
    chunk_id: str
    file_path: str | None
    language: str | None
    symbol_name: str | None
    start_line: int | None
    end_line: int | None
    snippet: str
    score: float | None

    @property
    def citation(self) -> str:
        if self.start_line and self.end_line and self.file_path:
            return f"{self.file_path}:{self.start_line}-{self.end_line}"
        return str(self.file_path or "unknown")


class RepositoryRetrievalEngine:
    def __init__(self, vector_store: VectorStore, settings: Settings) -> None:
        self.vector_store = vector_store
        self.settings = settings
        self.embedding_provider = OpenAIEmbeddingProvider(settings.openai_api_key, settings.openai_embedding_model)

    def retrieve(self, repository_id: int, query: str, *, filters: RetrievalFilters | None = None, top_k: int | None = None) -> list[RetrievedChunk]:
        metadata_filters = None
        if filters:
            metadata_filters = {"file_path": filters.file_path, "language": filters.language, "symbol_name": filters.symbol_name}
        query_embedding = self.embedding_provider.embed_texts([query])[0]
        return self.vector_store.query_chunks(
            repository_id,
            query_embedding,
            limit=top_k or self.settings.retrieval_top_k,
            metadata_filters=metadata_filters,
        )

    def fetch_by_path(self, repository_id: int, file_path: str) -> list[RetrievedChunk]:
        return self.vector_store.fetch_chunks(repository_id, metadata_filters={"file_path": file_path})

    def search(self, repository_id: int, query: str, *, top_k: int | None = None, filters: RetrievalFilters | None = None) -> list[SearchHit]:
        chunks = self.retrieve(repository_id, query, filters=filters, top_k=top_k)
        hits: list[SearchHit] = []
        for chunk in chunks:
            metadata = chunk.metadata
            hits.append(
                SearchHit(
                    chunk_id=chunk.chunk_id,
                    file_path=metadata.get("file_path"),
                    language=metadata.get("language"),
                    symbol_name=metadata.get("symbol_name"),
                    start_line=metadata.get("start_line"),
                    end_line=metadata.get("end_line"),
                    snippet=self._clip_snippet(chunk.text),
                    score=self._score(chunk),
                )
            )
        return hits

    def citation_lines(self, chunks: list[RetrievedChunk]) -> list[str]:
        citations: list[str] = []
        for chunk in chunks:
            metadata = chunk.metadata
            file_path = metadata.get("file_path", "unknown")
            start_line = metadata.get("start_line")
            end_line = metadata.get("end_line")
            if start_line and end_line:
                citations.append(f"{file_path}:{start_line}-{end_line}")
            else:
                citations.append(str(file_path))
        return citations

    def context_snippets(self, chunks: list[RetrievedChunk], *, max_context_chars: int | None = None) -> list[str]:
        rendered = []
        limit = max_context_chars or self.settings.prompt_max_context_chars
        used = 0
        for chunk in chunks:
            metadata = chunk.metadata
            header = f"[{metadata.get('file_path')}:{metadata.get('start_line')}-{metadata.get('end_line')}]"
            snippet = f"{header}\n{chunk.text}"
            if used + len(snippet) > limit:
                remaining = limit - used
                if remaining <= 0:
                    break
                snippet = snippet[:remaining]
            rendered.append(snippet)
            used += len(snippet)
        return rendered

    def _clip_snippet(self, text: str, width: int = 360) -> str:
        cleaned = " ".join(text.split())
        return cleaned if len(cleaned) <= width else cleaned[: width - 1].rstrip() + "…"

    def _score(self, chunk: RetrievedChunk) -> float | None:
        if chunk.distance is None:
            return None
        return round(max(0.0, 1.0 - float(chunk.distance)), 4)

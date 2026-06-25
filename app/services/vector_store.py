from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class RetrievedChunk:
    chunk_id: str
    text: str
    metadata: dict[str, Any]
    distance: float | None = None


class VectorStore(ABC):
    @abstractmethod
    def upsert_chunks(self, repository_id: int, chunks: list[dict[str, Any]], embeddings: list[list[float]]) -> None:
        raise NotImplementedError

    @abstractmethod
    def query_chunks(
        self,
        repository_id: int,
        query_embedding: list[float],
        *,
        limit: int,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        raise NotImplementedError

    @abstractmethod
    def fetch_chunks(
        self,
        repository_id: int,
        *,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        raise NotImplementedError


class ChromaVectorStore(VectorStore):
    def __init__(self, persist_dir: str) -> None:
        self.persist_dir = persist_dir
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        import chromadb

        self.client = chromadb.PersistentClient(path=persist_dir)

    def _collection_name(self, repository_id: int) -> str:
        return f"repository_{repository_id}"

    def upsert_chunks(self, repository_id: int, chunks: list[dict[str, Any]], embeddings: list[list[float]]) -> None:
        collection = self.client.get_or_create_collection(name=self._collection_name(repository_id))
        ids = [chunk["id"] for chunk in chunks]
        documents = [chunk["text"] for chunk in chunks]
        metadatas = [{key: value for key, value in chunk["metadata"].items() if value is not None} for chunk in chunks]
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)

    def _collection(self, repository_id: int):
        return self.client.get_or_create_collection(name=self._collection_name(repository_id))

    def _build_where(self, repository_id: int, metadata_filters: dict[str, Any] | None) -> dict[str, Any]:
        clauses: list[dict[str, Any]] = [{"repo_id": repository_id}]
        if metadata_filters:
            clauses.extend({key: value} for key, value in metadata_filters.items() if value is not None)
        if len(clauses) == 1:
            return clauses[0]
        return {"$and": clauses}

    def query_chunks(
        self,
        repository_id: int,
        query_embedding: list[float],
        *,
        limit: int,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        collection = self._collection(repository_id)
        where = self._build_where(repository_id, metadata_filters)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        ids = results.get("ids", [[]])[0]
        chunks: list[RetrievedChunk] = []
        for index, document in enumerate(documents):
            chunks.append(
                RetrievedChunk(
                    chunk_id=ids[index],
                    text=document,
                    metadata=metadatas[index] or {},
                    distance=distances[index] if index < len(distances) else None,
                )
            )
        return chunks

    def fetch_chunks(
        self,
        repository_id: int,
        *,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        collection = self._collection(repository_id)
        where = self._build_where(repository_id, metadata_filters)
        results = collection.get(where=where, include=["documents", "metadatas"])
        documents = results.get("documents", []) or []
        metadatas = results.get("metadatas", []) or []
        ids = results.get("ids", []) or []
        chunks: list[RetrievedChunk] = []
        for index, document in enumerate(documents):
            chunks.append(
                RetrievedChunk(
                    chunk_id=ids[index],
                    text=document,
                    metadata=metadatas[index] or {},
                )
            )
        return chunks
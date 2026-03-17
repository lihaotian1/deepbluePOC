from __future__ import annotations

from threading import Lock
from uuid import uuid4

from app.schemas import Chunk, ChunkCompareResult, DocumentSession


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, DocumentSession] = {}
        self._lock = Lock()

    def create(self, *, source_file_name: str, chunks: list[Chunk]) -> DocumentSession:
        session = DocumentSession(
            doc_id=str(uuid4()),
            source_file_name=source_file_name,
            chunks=chunks,
            compare_results=[],
        )
        with self._lock:
            self._sessions[session.doc_id] = session
        return session

    def get(self, doc_id: str) -> DocumentSession | None:
        return self._sessions.get(doc_id)

    def update_chunks(self, doc_id: str, updates: dict[int, str]) -> DocumentSession | None:
        with self._lock:
            session = self._sessions.get(doc_id)
            if session is None:
                return None

            next_chunks: list[Chunk] = []
            for chunk in session.chunks:
                if chunk.chunk_id in updates:
                    next_chunks.append(chunk.model_copy(update={"content": updates[chunk.chunk_id]}))
                else:
                    next_chunks.append(chunk)

            updated = session.model_copy(update={"chunks": next_chunks, "compare_results": []})
            self._sessions[doc_id] = updated
            return updated

    def save_results(self, doc_id: str, results: list[ChunkCompareResult]) -> DocumentSession | None:
        with self._lock:
            session = self._sessions.get(doc_id)
            if session is None:
                return None
            updated = session.model_copy(update={"compare_results": results})
            self._sessions[doc_id] = updated
            return updated

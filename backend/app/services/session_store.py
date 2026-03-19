from __future__ import annotations

from threading import Lock
from uuid import uuid4

from app.schemas import Chunk, ChunkCompareProgress, ChunkCompareResult, DocumentSession


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, DocumentSession] = {}
        self._lock = Lock()

    def create(self, *, source_file_name: str, chunks: list[Chunk]) -> DocumentSession:
        session = DocumentSession(
            doc_id=str(uuid4()),
            source_file_name=source_file_name,
            chunks=chunks,
            compare_results_by_kb={},
            compare_progress_by_kb={},
            submitted_for_review=False,
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

            updated = session.model_copy(
                update={
                    "chunks": next_chunks,
                    "compare_results_by_kb": {},
                    "compare_progress_by_kb": {},
                    "submitted_for_review": False,
                }
            )
            self._sessions[doc_id] = updated
            return updated

    def save_review_state(
        self,
        doc_id: str,
        *,
        compare_results_by_kb: dict[str, list[ChunkCompareResult]],
        submitted_for_review: bool,
    ) -> DocumentSession | None:
        with self._lock:
            session = self._sessions.get(doc_id)
            if session is None:
                return None

            next_results_by_kb = {
                kb_file: list(results)
                for kb_file, results in compare_results_by_kb.items()
            }
            next_progress_by_kb = {
                kb_file: self._progress_from_results(session.chunks, results)
                for kb_file, results in next_results_by_kb.items()
            }
            updated = session.model_copy(
                update={
                    "compare_results_by_kb": next_results_by_kb,
                    "compare_progress_by_kb": next_progress_by_kb,
                    "submitted_for_review": submitted_for_review,
                }
            )
            self._sessions[doc_id] = updated
            return updated

    def save_results(self, doc_id: str, kb_file: str, results: list[ChunkCompareResult]) -> DocumentSession | None:
        with self._lock:
            session = self._sessions.get(doc_id)
            if session is None:
                return None
            compare_results_by_kb = dict(session.compare_results_by_kb)
            compare_results_by_kb[kb_file] = results
            progress = self._build_progress_for_kb(session, kb_file)
            result_map = {result.chunk_id: result for result in results}
            for chunk in session.chunks:
                chunk_result = result_map.get(chunk.chunk_id)
                if chunk_result is None:
                    progress[chunk.chunk_id] = ChunkCompareProgress(status="pending")
                    continue
                progress[chunk.chunk_id] = ChunkCompareProgress(status="succeeded", result=chunk_result)

            compare_progress_by_kb = dict(session.compare_progress_by_kb)
            compare_progress_by_kb[kb_file] = progress
            updated = session.model_copy(
                update={
                    "compare_results_by_kb": compare_results_by_kb,
                    "compare_progress_by_kb": compare_progress_by_kb,
                    "submitted_for_review": False,
                }
            )
            self._sessions[doc_id] = updated
            return updated

    def get_resumable_chunks(self, doc_id: str, kb_file: str) -> tuple[list[Chunk], int] | None:
        with self._lock:
            session = self._sessions.get(doc_id)
            if session is None:
                return None

            progress = self._build_progress_for_kb(session, kb_file)
            compare_progress_by_kb = dict(session.compare_progress_by_kb)
            compare_progress_by_kb[kb_file] = progress
            compare_results_by_kb = dict(session.compare_results_by_kb)
            compare_results_by_kb[kb_file] = self._results_from_progress(session.chunks, progress)
            updated = session.model_copy(
                update={
                    "compare_results_by_kb": compare_results_by_kb,
                    "compare_progress_by_kb": compare_progress_by_kb,
                    "submitted_for_review": False,
                }
            )
            self._sessions[doc_id] = updated

            resumable_chunks = [
                chunk
                for chunk in session.chunks
                if progress[chunk.chunk_id].status in {"pending", "failed"}
            ]
            skipped_count = sum(1 for record in progress.values() if record.status == "succeeded")
            return resumable_chunks, skipped_count

    def mark_chunks_running(self, doc_id: str, kb_file: str, chunk_ids: list[int]) -> DocumentSession | None:
        return self._update_progress(doc_id, kb_file, chunk_ids, status="running", error_message="")

    def mark_chunks_failed(self, doc_id: str, kb_file: str, chunk_ids: list[int], error_message: str) -> DocumentSession | None:
        return self._update_progress(doc_id, kb_file, chunk_ids, status="failed", error_message=error_message)

    def save_chunk_result(self, doc_id: str, kb_file: str, result: ChunkCompareResult) -> DocumentSession | None:
        with self._lock:
            session = self._sessions.get(doc_id)
            if session is None:
                return None

            progress = self._build_progress_for_kb(session, kb_file)
            progress[result.chunk_id] = ChunkCompareProgress(status="succeeded", result=result)
            compare_progress_by_kb = dict(session.compare_progress_by_kb)
            compare_progress_by_kb[kb_file] = progress
            compare_results_by_kb = dict(session.compare_results_by_kb)
            compare_results_by_kb[kb_file] = self._results_from_progress(session.chunks, progress)
            updated = session.model_copy(
                update={
                    "compare_results_by_kb": compare_results_by_kb,
                    "compare_progress_by_kb": compare_progress_by_kb,
                    "submitted_for_review": False,
                }
            )
            self._sessions[doc_id] = updated
            return updated

    def build_compare_summary(self, doc_id: str, kb_file: str, skipped_count: int) -> dict[str, int] | None:
        with self._lock:
            session = self._sessions.get(doc_id)
            if session is None:
                return None

            progress = self._build_progress_for_kb(session, kb_file)
            return {
                "total": len(session.chunks),
                "succeeded": sum(1 for record in progress.values() if record.status == "succeeded"),
                "failed": sum(1 for record in progress.values() if record.status == "failed"),
                "skipped": skipped_count,
            }

    def _update_progress(
        self,
        doc_id: str,
        kb_file: str,
        chunk_ids: list[int],
        *,
        status: str,
        error_message: str,
    ) -> DocumentSession | None:
        with self._lock:
            session = self._sessions.get(doc_id)
            if session is None:
                return None

            progress = self._build_progress_for_kb(session, kb_file)
            for chunk_id in chunk_ids:
                existing = progress.get(chunk_id, ChunkCompareProgress())
                progress[chunk_id] = existing.model_copy(update={"status": status, "error_message": error_message})

            compare_progress_by_kb = dict(session.compare_progress_by_kb)
            compare_progress_by_kb[kb_file] = progress
            compare_results_by_kb = dict(session.compare_results_by_kb)
            compare_results_by_kb[kb_file] = self._results_from_progress(session.chunks, progress)
            updated = session.model_copy(
                update={
                    "compare_results_by_kb": compare_results_by_kb,
                    "compare_progress_by_kb": compare_progress_by_kb,
                    "submitted_for_review": False,
                }
            )
            self._sessions[doc_id] = updated
            return updated

    @staticmethod
    def _progress_from_results(chunks: list[Chunk], results: list[ChunkCompareResult]) -> dict[int, ChunkCompareProgress]:
        progress: dict[int, ChunkCompareProgress] = {
            chunk.chunk_id: ChunkCompareProgress(status="pending")
            for chunk in chunks
        }
        for result in results:
            progress[result.chunk_id] = ChunkCompareProgress(status="succeeded", result=result)
        return progress

    @staticmethod
    def _build_progress_for_kb(session: DocumentSession, kb_file: str) -> dict[int, ChunkCompareProgress]:
        existing = session.compare_progress_by_kb.get(kb_file, {})
        progress: dict[int, ChunkCompareProgress] = {}
        for chunk in session.chunks:
            progress[chunk.chunk_id] = existing.get(chunk.chunk_id, ChunkCompareProgress())
        return progress

    @staticmethod
    def _results_from_progress(
        chunks: list[Chunk], progress: dict[int, ChunkCompareProgress]
    ) -> list[ChunkCompareResult]:
        results: list[ChunkCompareResult] = []
        for chunk in chunks:
            record = progress.get(chunk.chunk_id)
            if record is None or record.status != "succeeded" or record.result is None:
                continue
            results.append(record.result)
        return results

from __future__ import annotations

from threading import Lock
from uuid import uuid4

from app.schemas import CompareRow, DocumentSession


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, DocumentSession] = {}
        self._lock = Lock()

    def create(self, *, source_file_name: str, document_text: str) -> DocumentSession:
        session = DocumentSession(
            doc_id=str(uuid4()),
            source_file_name=source_file_name,
            document_text=document_text,
            compare_rows=[],
            chunks=[],
            compare_results_by_kb={},
            compare_progress_by_kb={},
            submitted_for_review=False,
        )
        with self._lock:
            self._sessions[session.doc_id] = session
        return session

    def get(self, doc_id: str) -> DocumentSession | None:
        return self._sessions.get(doc_id)

    def save_compare_rows(self, doc_id: str, rows: list[CompareRow]) -> DocumentSession | None:
        with self._lock:
            session = self._sessions.get(doc_id)
            if session is None:
                return None

            updated = session.model_copy(
                update={
                    "compare_rows": list(rows),
                    "submitted_for_review": False,
                }
            )
            self._sessions[doc_id] = updated
            return updated

    def save_review_state(
        self,
        doc_id: str,
        *,
        compare_rows: list[CompareRow],
        submitted_for_review: bool,
    ) -> DocumentSession | None:
        with self._lock:
            session = self._sessions.get(doc_id)
            if session is None:
                return None

            updated = session.model_copy(
                update={
                    "compare_rows": list(compare_rows),
                    "submitted_for_review": submitted_for_review,
                }
            )
            self._sessions[doc_id] = updated
            return updated

from __future__ import annotations

from threading import Lock
from uuid import uuid4

from app.schemas import CompareAnalysisResult, CompareRow, DocumentSession, OtherRequirementRow


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, DocumentSession] = {}
        self._compare_cache: dict[str, CompareAnalysisResult] = {}
        self._lock = Lock()

    def create(self, *, source_file_name: str, document_text: str) -> DocumentSession:
        session = DocumentSession(
            doc_id=str(uuid4()),
            source_file_name=source_file_name,
            document_text=document_text,
            compare_rows=[],
            other_requirements=[],
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
                    "other_requirements": [row.model_copy(deep=True) for row in session.other_requirements],
                    "submitted_for_review": False,
                }
            )
            self._sessions[doc_id] = updated
            return updated

    def save_compare_analysis(
        self,
        doc_id: str,
        *,
        compare_rows: list[CompareRow],
        other_requirements: list[OtherRequirementRow],
    ) -> DocumentSession | None:
        with self._lock:
            session = self._sessions.get(doc_id)
            if session is None:
                return None

            updated = session.model_copy(
                update={
                    "compare_rows": list(compare_rows),
                    "other_requirements": list(other_requirements),
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
                    "other_requirements": [row.model_copy(deep=True) for row in session.other_requirements],
                    "submitted_for_review": submitted_for_review,
                }
            )
            self._sessions[doc_id] = updated
            return updated

    def get_compare_cache(self, cache_key: str) -> CompareAnalysisResult | None:
        with self._lock:
            analysis = self._compare_cache.get(cache_key)
            if analysis is None:
                return None
            return analysis.model_copy(deep=True)

    def save_compare_cache(self, cache_key: str, analysis: CompareAnalysisResult) -> None:
        with self._lock:
            self._compare_cache[cache_key] = analysis.model_copy(deep=True)

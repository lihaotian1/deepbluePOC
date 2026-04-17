from __future__ import annotations

import hashlib
import json
import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import httpx

from app.api.deps import get_knowledge_base_manager, get_matcher_llm, get_session_store
from app.schemas import CompareRow
from app.services.compare_profiles import STANDARD_KB_FILE_NAME, get_compare_profile
from app.services.knowledge_base_manager import KnowledgeBaseManager
from app.services.llm_client import OpenAICompatibleMatcherLLM
from app.services.session_store import SessionStore


router = APIRouter(prefix="/documents", tags=["compare"])


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, separators=(',', ':'))}\n\n"


def _build_row_id(entry_id: str, source_excerpt: str) -> str:
    digest = hashlib.sha1(f"{entry_id}\n{source_excerpt}".encode("utf-8")).hexdigest()[:12]
    return f"{entry_id}::{digest}"


def _format_compare_error_message(exc: Exception) -> str:
    if isinstance(exc, httpx.ReadTimeout):
        return "智能分析服务响应超时，请稍后重试。"
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429:
        return "智能分析服务繁忙，请稍后重试。"

    message = str(exc).strip()
    if message == "LLM returned an empty assistant message.":
        return "当前模型服务返回空响应，请检查模型或网关兼容性。"
    if message:
        return message
    return exc.__class__.__name__


def _is_conflict_summary(summary: str) -> bool:
    return summary.startswith("存在冲突：")


def _normalize_excerpt_for_compare(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text).strip().lower()
    normalized = normalized.replace("–", "-").replace("—", "-")
    return normalized


def _looks_like_same_requirement(left: str, right: str) -> bool:
    if left == right:
        return True
    if left in right or right in left:
        return True

    left_tokens = {token for token in re.split(r"[^a-z0-9\u4e00-\u9fff]+", left) if token}
    right_tokens = {token for token in re.split(r"[^a-z0-9\u4e00-\u9fff]+", right) if token}
    if not left_tokens or not right_tokens:
        return False

    overlap = len(left_tokens & right_tokens)
    smaller = min(len(left_tokens), len(right_tokens))
    return smaller > 0 and overlap / smaller >= 0.8


def _same_brief_summary(left: str, right: str) -> bool:
    return left.strip() and right.strip() and left.strip() == right.strip()


def _pick_preferred_row(current: CompareRow, candidate: CompareRow) -> CompareRow:
    current_conflict = _is_conflict_summary(current.difference_summary)
    candidate_conflict = _is_conflict_summary(candidate.difference_summary)
    if candidate_conflict and not current_conflict:
        return candidate
    if current_conflict and not candidate_conflict:
        return current
    if len(candidate.source_excerpt) > len(current.source_excerpt):
        return candidate
    return current


def _coalesce_compare_rows(rows: list[CompareRow]) -> list[CompareRow]:
    grouped: dict[str, list[CompareRow]] = {}
    for row in rows:
        grouped.setdefault(row.kb_entry_id, []).append(row)

    merged_rows: list[CompareRow] = []
    for entry_rows in grouped.values():
        has_conflict = any(_is_conflict_summary(row.difference_summary) for row in entry_rows)
        filtered_rows = [row for row in entry_rows if _is_conflict_summary(row.difference_summary)] if has_conflict else entry_rows

        entry_merged: list[CompareRow] = []
        for row in filtered_rows:
            normalized_excerpt = _normalize_excerpt_for_compare(row.source_excerpt)
            matched_index = next(
                (
                    index
                    for index, existing in enumerate(entry_merged)
                    if (
                        _same_brief_summary(row.difference_summary_brief, existing.difference_summary_brief)
                        or _looks_like_same_requirement(normalized_excerpt, _normalize_excerpt_for_compare(existing.source_excerpt))
                    )
                ),
                None,
            )
            if matched_index is None:
                entry_merged.append(row)
                continue

            entry_merged[matched_index] = _pick_preferred_row(entry_merged[matched_index], row)

        merged_rows.extend(entry_merged)

    return merged_rows


@router.post("/{doc_id}/compare/stream")
async def compare_stream(
    doc_id: str,
    store: SessionStore = Depends(get_session_store),
    manager: KnowledgeBaseManager = Depends(get_knowledge_base_manager),
    llm: OpenAICompatibleMatcherLLM = Depends(get_matcher_llm),
):
    session = store.get(doc_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Document session not found")

    try:
        profile = get_compare_profile(STANDARD_KB_FILE_NAME)
        kb_path = manager.resolve_file(profile.file_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Knowledge base file not found") from exc

    kb = profile.loader(kb_path)

    async def event_generator():
        yield _sse_event(
            "compare_started",
            {
                "doc_id": doc_id,
                "source_file_name": session.source_file_name,
            },
        )

        try:
            raw_rows = await llm.compare_document_rows(
                document_title=session.source_file_name,
                document_text=session.document_text,
                entries=kb.entries,
            )
        except Exception as exc:
            yield _sse_event(
                "error",
                {
                    "doc_id": doc_id,
                    "message": _format_compare_error_message(exc),
                },
            )
            return

        entry_map = {entry.entry_id: entry for entry in kb.entries}
        compare_rows: list[CompareRow] = []
        seen_pairs: set[tuple[str, str]] = set()
        for row in raw_rows:
            entry_id = row["entry_id"]
            source_excerpt = row["source_excerpt"]
            dedupe_key = (entry_id, source_excerpt)
            if dedupe_key in seen_pairs:
                continue

            entry = entry_map.get(entry_id)
            if entry is None:
                continue

            seen_pairs.add(dedupe_key)
            compare_rows.append(
                CompareRow(
                    row_id=_build_row_id(entry_id, source_excerpt),
                    chapter_title=row["chapter_title"],
                    source_excerpt=source_excerpt,
                    kb_entry_id=entry.entry_id,
                    kb_entry_text=entry.text,
                    difference_summary_brief=row.get("difference_summary_brief", row["difference_summary"]),
                    difference_summary=row["difference_summary"],
                    type_code=entry.type_code if entry.type_code in {"P", "A", "B", "C"} else "C",
                )
            )

        compare_rows = _coalesce_compare_rows(compare_rows)
        store.save_compare_rows(doc_id, compare_rows)

        total = len(compare_rows)
        for index, row in enumerate(compare_rows, start=1):
            yield _sse_event(
                "compare_row",
                {
                    "doc_id": doc_id,
                    "index": index,
                    "total": total,
                    "result": row.model_dump(),
                },
            )

        yield _sse_event(
            "compare_done",
            {
                "doc_id": doc_id,
                "row_count": total,
            },
        )

    return StreamingResponse(event_generator(), media_type="text/event-stream")

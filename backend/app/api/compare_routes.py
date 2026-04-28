from __future__ import annotations

import hashlib
import json
import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import httpx

from app.api.deps import get_knowledge_base_manager, get_matcher_llm, get_session_store
from app.schemas import CompareAnalysisResult, CompareRow, OtherRequirementRow
from app.services.compare_profiles import STANDARD_KB_FILE_NAME, get_compare_profile
from app.services.knowledge_base_manager import KnowledgeBaseManager
from app.services.llm_client import OpenAICompatibleMatcherLLM
from app.services.prompt_builder import DOCUMENT_COMPARE_PIPELINE_VERSION
from app.services.session_store import SessionStore


router = APIRouter(prefix="/documents", tags=["compare"])


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, separators=(',', ':'))}\n\n"


def _build_row_id(entry_id: str, source_excerpt: str) -> str:
    digest = hashlib.sha1(f"{entry_id}\n{source_excerpt}".encode("utf-8")).hexdigest()[:12]
    return f"{entry_id}::{digest}"


def _build_other_requirement_row_id(chapter_title: str, source_excerpt: str) -> str:
    digest = hashlib.sha1(f"{chapter_title}\n{source_excerpt}".encode("utf-8")).hexdigest()[:12]
    return f"other::{digest}"


def _build_compare_cache_key(*, document_text: str, kb_entries, model: str, base_url: str) -> str:
    serialized = json.dumps(
        {
            "document_text": document_text,
            "kb_entries": [
                {
                    "entry_id": entry.entry_id,
                    "text": entry.text,
                    "type_code": entry.type_code,
                }
                for entry in kb_entries
            ],
            "model": model,
            "base_url": base_url,
            "prompt_version": DOCUMENT_COMPARE_PIPELINE_VERSION,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


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
        group_key = _normalize_excerpt_for_compare(row.kb_entry_text) or row.kb_entry_id
        grouped.setdefault(group_key, []).append(row)

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


def _with_source_order(candidate_excerpts: list[dict[str, str]]) -> list[dict[str, object]]:
    ordered: list[dict[str, object]] = []
    for index, item in enumerate(candidate_excerpts, start=1):
        source_excerpt = str(item.get("source_excerpt", "")).strip()
        if not source_excerpt:
            continue
        ordered.append(
            {
                "chapter_title": str(item.get("chapter_title", "")).strip() or "未识别标题",
                "source_excerpt": source_excerpt,
                "source_order": index,
            }
        )
    return ordered


def _filter_unmatched_candidates(
    candidate_excerpts: list[dict[str, object]],
    matched_rows: list[CompareRow],
) -> list[dict[str, object]]:
    unmatched: list[dict[str, object]] = []
    matched_excerpts = [_normalize_excerpt_for_compare(row.source_excerpt) for row in matched_rows]
    for candidate in candidate_excerpts:
        source_excerpt = str(candidate.get("source_excerpt", "")).strip()
        if not source_excerpt:
            continue
        normalized_source = _normalize_excerpt_for_compare(source_excerpt)
        is_matched = any(_looks_like_same_requirement(normalized_source, matched_excerpt) for matched_excerpt in matched_excerpts)
        if is_matched:
            continue
        unmatched.append(candidate)
    return unmatched


def _match_candidate_for_other_requirement(
    source_excerpt: str,
    candidate_excerpts: list[dict[str, object]],
) -> dict[str, object] | None:
    normalized_source = _normalize_excerpt_for_compare(source_excerpt)
    source_tokens = {token for token in re.split(r"[^a-z0-9\u4e00-\u9fff]+", normalized_source) if token}
    best_candidate: dict[str, object] | None = None
    best_score: tuple[float, int] | None = None

    for candidate in candidate_excerpts:
        candidate_excerpt = str(candidate.get("source_excerpt", "")).strip()
        if not candidate_excerpt:
            continue
        normalized_candidate = _normalize_excerpt_for_compare(candidate_excerpt)
        if not _looks_like_same_requirement(normalized_source, normalized_candidate):
            continue

        if normalized_source == normalized_candidate:
            score = (3.0, len(candidate_excerpt))
        elif normalized_candidate in normalized_source or normalized_source in normalized_candidate:
            score = (2.0, len(candidate_excerpt))
        else:
            candidate_tokens = {token for token in re.split(r"[^a-z0-9\u4e00-\u9fff]+", normalized_candidate) if token}
            smaller = min(len(source_tokens), len(candidate_tokens))
            overlap = len(source_tokens & candidate_tokens)
            ratio = overlap / smaller if smaller else 0.0
            score = (1.0 + ratio, len(candidate_excerpt))

        if best_score is None or score > best_score:
            best_candidate = candidate
            best_score = score

    return best_candidate


def _resolve_minimal_candidate_excerpt(
    source_excerpt: str,
    candidate_excerpts: list[dict[str, object]],
) -> str:
    candidate = _match_candidate_for_other_requirement(source_excerpt, candidate_excerpts)
    if candidate is None:
        return source_excerpt

    normalized_excerpt = str(candidate.get("source_excerpt", "")).strip()
    return normalized_excerpt or source_excerpt


def _build_other_requirement_rows(
    raw_rows: list[dict[str, str]],
    candidate_excerpts: list[dict[str, object]],
) -> list[OtherRequirementRow]:
    output: list[OtherRequirementRow] = []
    seen_row_ids: set[str] = set()
    for row in raw_rows:
        source_excerpt = row.get("source_excerpt", "")
        candidate = _match_candidate_for_other_requirement(source_excerpt, candidate_excerpts)
        if candidate is None:
            continue

        chapter_title = str(candidate.get("chapter_title", "")).strip() or "未识别标题"
        normalized_excerpt = str(candidate.get("source_excerpt", "")).strip()
        row_id = _build_other_requirement_row_id(chapter_title, normalized_excerpt)
        if row_id in seen_row_ids:
            continue
        seen_row_ids.add(row_id)
        output.append(
            OtherRequirementRow(
                row_id=row_id,
                chapter_title=chapter_title,
                source_excerpt=normalized_excerpt,
                summary=row.get("summary", "").strip(),
                source_order=int(candidate.get("source_order", 0) or 0),
            )
        )

    return sorted(output, key=lambda item: item.source_order)


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
    cache_key = _build_compare_cache_key(
        document_text=session.document_text,
        kb_entries=kb.entries,
        model=getattr(llm, "model", "test-model"),
        base_url=getattr(llm, "base_url", "test-base-url"),
    )

    async def event_generator():
        yield _sse_event(
            "compare_started",
            {
                "doc_id": doc_id,
                "source_file_name": session.source_file_name,
            },
        )
        store.save_compare_analysis(doc_id, compare_rows=[], other_requirements=[])

        cached_analysis = store.get_compare_cache(cache_key)
        if cached_analysis is not None:
            store.save_compare_analysis(
                doc_id,
                compare_rows=cached_analysis.compare_rows,
                other_requirements=cached_analysis.other_requirements,
            )
            for row in cached_analysis.compare_rows:
                yield _sse_event(
                    "compare_row",
                    {
                        "doc_id": doc_id,
                        "result": row.model_dump(),
                    },
                )
            for row in cached_analysis.other_requirements:
                yield _sse_event(
                    "other_requirement_row",
                    {
                        "doc_id": doc_id,
                        "result": row.model_dump(),
                    },
                )
            yield _sse_event(
                "other_requirement_done",
                {
                    "doc_id": doc_id,
                    "row_count": len(cached_analysis.other_requirements),
                },
            )
            yield _sse_event(
                "compare_done",
                {
                    "doc_id": doc_id,
                    "row_count": len(cached_analysis.compare_rows),
                    "other_requirement_count": len(cached_analysis.other_requirements),
                },
            )
            return

        try:
            candidate_excerpts = _with_source_order(
                await llm.extract_document_candidates(
                    document_title=session.source_file_name,
                    document_text=session.document_text,
                )
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

        if not candidate_excerpts:
            empty_analysis = CompareAnalysisResult(compare_rows=[], other_requirements=[])
            store.save_compare_cache(cache_key, empty_analysis)
            yield _sse_event(
                "other_requirement_done",
                {
                    "doc_id": doc_id,
                    "row_count": 0,
                },
            )
            yield _sse_event(
                "compare_done",
                {
                    "doc_id": doc_id,
                    "row_count": 0,
                    "other_requirement_count": 0,
                },
            )
            return

        entry_map = {entry.entry_id: entry for entry in kb.entries}
        def build_compare_row(row: dict[str, str]) -> CompareRow | None:
            entry_id = row["entry_id"]
            source_excerpt = _resolve_minimal_candidate_excerpt(row["source_excerpt"], candidate_excerpts)
            entry = entry_map.get(entry_id)
            if entry is None:
                return None
            return CompareRow(
                row_id=_build_row_id(entry_id, source_excerpt),
                chapter_title=row["chapter_title"],
                source_excerpt=source_excerpt,
                kb_entry_id=entry.entry_id,
                kb_entry_text=entry.text,
                difference_summary_brief=row.get("difference_summary_brief", row["difference_summary"]),
                difference_summary=row["difference_summary"],
                type_code=entry.type_code if entry.type_code in {"P", "A", "B", "C"} else "C",
            )

        if hasattr(llm, "stream_compare_document_rows"):
            compare_rows: list[CompareRow] = []
            current_rows: list[CompareRow] = []
            current_rows_by_id: dict[str, CompareRow] = {}
            seen_pairs: set[tuple[str, str]] = set()
            try:
                async for row in llm.stream_compare_document_rows(
                    document_title=session.source_file_name,
                    document_text=session.document_text,
                    entries=kb.entries,
                    candidate_excerpts=[
                        {
                            "chapter_title": str(item["chapter_title"]),
                            "source_excerpt": str(item["source_excerpt"]),
                        }
                        for item in candidate_excerpts
                    ],
                ):
                    entry_id = row["entry_id"]
                    source_excerpt = row["source_excerpt"]
                    dedupe_key = (entry_id, source_excerpt)
                    if dedupe_key in seen_pairs:
                        continue

                    next_row = build_compare_row(row)
                    if next_row is None:
                        continue

                    seen_pairs.add(dedupe_key)
                    compare_rows.append(next_row)

                    next_rows = _coalesce_compare_rows(compare_rows)
                    next_rows_by_id = {item.row_id: item for item in next_rows}

                    for removed_row_id in current_rows_by_id.keys() - next_rows_by_id.keys():
                        yield _sse_event(
                            "compare_row_remove",
                            {
                                "doc_id": doc_id,
                                "row_id": removed_row_id,
                            },
                        )

                    for row_id, emitted_row in next_rows_by_id.items():
                        existing = current_rows_by_id.get(row_id)
                        if existing is not None and existing.model_dump() == emitted_row.model_dump():
                            continue
                        yield _sse_event(
                            "compare_row",
                            {
                                "doc_id": doc_id,
                                "result": emitted_row.model_dump(),
                            },
                        )

                    current_rows = next_rows
                    current_rows_by_id = next_rows_by_id
                    store.save_compare_rows(doc_id, current_rows)
            except Exception as exc:
                yield _sse_event(
                    "error",
                    {
                        "doc_id": doc_id,
                        "message": _format_compare_error_message(exc),
                    },
                )
                return

            matched_excerpts = [
                {"chapter_title": row.chapter_title, "source_excerpt": row.source_excerpt}
                for row in current_rows
            ]
            unmatched_candidates = _filter_unmatched_candidates(candidate_excerpts, current_rows)
            try:
                raw_other_rows = await llm.extract_other_requirements(
                    document_title=session.source_file_name,
                    candidate_excerpts=unmatched_candidates,
                    matched_excerpts=matched_excerpts,
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

            other_rows = _build_other_requirement_rows(raw_other_rows, unmatched_candidates)
            store.save_compare_analysis(doc_id, compare_rows=current_rows, other_requirements=other_rows)
            for row in other_rows:
                yield _sse_event(
                    "other_requirement_row",
                    {
                        "doc_id": doc_id,
                        "result": row.model_dump(),
                    },
                )
            yield _sse_event(
                "other_requirement_done",
                {
                    "doc_id": doc_id,
                    "row_count": len(other_rows),
                },
            )
            yield _sse_event(
                "compare_done",
                {
                    "doc_id": doc_id,
                    "row_count": len(current_rows),
                    "other_requirement_count": len(other_rows),
                },
            )
            store.save_compare_cache(
                cache_key,
                CompareAnalysisResult(compare_rows=current_rows, other_requirements=other_rows),
            )
            return

        try:
            raw_rows = await llm.compare_document_rows(
                document_title=session.source_file_name,
                document_text=session.document_text,
                entries=kb.entries,
                candidate_excerpts=[
                    {
                        "chapter_title": str(item["chapter_title"]),
                        "source_excerpt": str(item["source_excerpt"]),
                    }
                    for item in candidate_excerpts
                ],
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

        compare_rows: list[CompareRow] = []
        seen_pairs: set[tuple[str, str]] = set()
        for row in raw_rows:
                entry_id = row["entry_id"]
                source_excerpt = row["source_excerpt"]
                dedupe_key = (entry_id, source_excerpt)
                if dedupe_key in seen_pairs:
                    continue

                next_row = build_compare_row(row)
                if next_row is None:
                    continue

                seen_pairs.add(dedupe_key)
                compare_rows.append(next_row)

        compare_rows = _coalesce_compare_rows(compare_rows)
        matched_excerpts = [
            {"chapter_title": row.chapter_title, "source_excerpt": row.source_excerpt}
            for row in compare_rows
        ]
        unmatched_candidates = _filter_unmatched_candidates(candidate_excerpts, compare_rows)
        try:
            raw_other_rows = await llm.extract_other_requirements(
                document_title=session.source_file_name,
                candidate_excerpts=unmatched_candidates,
                matched_excerpts=matched_excerpts,
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

        other_rows = _build_other_requirement_rows(raw_other_rows, unmatched_candidates)
        store.save_compare_analysis(doc_id, compare_rows=compare_rows, other_requirements=other_rows)
        store.save_compare_cache(
            cache_key,
            CompareAnalysisResult(compare_rows=compare_rows, other_requirements=other_rows),
        )

        for row in compare_rows:
            yield _sse_event(
                "compare_row",
                {
                    "doc_id": doc_id,
                    "result": row.model_dump(),
                },
            )
        for row in other_rows:
            yield _sse_event(
                "other_requirement_row",
                {
                    "doc_id": doc_id,
                    "result": row.model_dump(),
                },
            )
        yield _sse_event(
            "other_requirement_done",
            {
                "doc_id": doc_id,
                "row_count": len(other_rows),
            },
        )

        yield _sse_event(
            "compare_done",
            {
                "doc_id": doc_id,
                "row_count": len(compare_rows),
                "other_requirement_count": len(other_rows),
            },
        )

    return StreamingResponse(event_generator(), media_type="text/event-stream")

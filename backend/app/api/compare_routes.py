from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.deps import get_knowledge_base_manager, get_matcher_llm, get_session_store
from app.schemas import CompareRequest
from app.services.compare_profiles import get_compare_profile
from app.services.knowledge_base_manager import KnowledgeBaseManager
from app.services.llm_client import OpenAICompatibleMatcherLLM
from app.services.matcher_service import MatcherService
from app.services.session_store import SessionStore


router = APIRouter(prefix="/documents", tags=["compare"])
BATCH_SIZE = 10


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, separators=(',', ':'))}\n\n"


@router.post("/{doc_id}/compare/stream")
async def compare_stream(
    doc_id: str,
    request: CompareRequest,
    store: SessionStore = Depends(get_session_store),
    manager: KnowledgeBaseManager = Depends(get_knowledge_base_manager),
    llm: OpenAICompatibleMatcherLLM = Depends(get_matcher_llm),
):
    session = store.get(doc_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Document session not found")

    selected_profiles = []
    for file_name in request.knowledge_base_files:
        try:
            profile = get_compare_profile(file_name)
            selected_profiles.append((profile, manager.resolve_file(file_name)))
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Knowledge base file not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    async def event_generator():
        total = len(session.chunks)
        for profile, kb_path in selected_profiles:
            matcher = MatcherService(kb=profile.loader(kb_path), llm=llm)
            results = []

            for start in range(0, total, BATCH_SIZE):
                chunk_batch = session.chunks[start : start + BATCH_SIZE]
                for offset, chunk in enumerate(chunk_batch, start=start + 1):
                    yield _sse_event(
                        "chunk_start",
                        {
                            "doc_id": doc_id,
                            "kb_file": profile.file_name,
                            "kb_display_name": profile.display_name,
                            "chunk_id": chunk.chunk_id,
                            "heading": chunk.heading,
                            "index": offset,
                            "total": total,
                        },
                    )

                try:
                    batch_results = await matcher.compare_chunks_with_trace(chunk_batch, batch_size=BATCH_SIZE)
                except Exception as exc:
                    for chunk in chunk_batch:
                        yield _sse_event(
                            "error",
                            {
                                "doc_id": doc_id,
                                "kb_file": profile.file_name,
                                "kb_display_name": profile.display_name,
                                "chunk_id": chunk.chunk_id,
                                "message": str(exc),
                            },
                        )
                    continue

                for result, trace in batch_results:
                    for trace_item in trace:
                        event_name = str(trace_item.get("event", "trace"))
                        yield _sse_event(
                            event_name,
                            {
                                "doc_id": doc_id,
                                "kb_file": profile.file_name,
                                "kb_display_name": profile.display_name,
                                **trace_item,
                            },
                        )

                    results.append(result)
                    yield _sse_event(
                        "chunk_result",
                        {
                            "doc_id": doc_id,
                            "kb_file": profile.file_name,
                            "kb_display_name": profile.display_name,
                            "result": result.model_dump(),
                        },
                    )

            store.save_results(doc_id, profile.file_name, results)

        yield _sse_event(
            "compare_done",
            {
                "doc_id": doc_id,
                "knowledge_base_files": [profile.file_name for profile, _ in selected_profiles],
                "total": total,
                "done": total,
            },
        )

    return StreamingResponse(event_generator(), media_type="text/event-stream")

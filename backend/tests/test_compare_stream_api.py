import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import compare_routes
from app.schemas import Chunk
from app.main import create_app
from app.services.compare_profiles import STANDARD_KB_FILE_NAME, TENDER_KB_FILE_NAME
from app.services.knowledge_base_manager import KnowledgeBaseManager


class FakeLLM:
    async def classify_categories_batch(self, *, chunks, category_keys, category_contexts=None):
        preferred_category = "非强制-报价行动" if "非强制-报价行动" in category_keys else category_keys[0]
        return {chunk_id: [preferred_category] for chunk_id, _ in chunks}

    async def match_items_batch(self, *, category, entries, chunks):
        output = {}
        for chunk in chunks:
            if isinstance(chunk, tuple):
                chunk_id = chunk[0]
                evidence_text = "这是正文。"
            else:
                chunk_id = chunk["chunk_id"]
                evidence_text = "这是正文。"

            output[chunk_id] = [
                {
                    "entry_id": entries[0].entry_id,
                    "reason": "直接支持：语义一致",
                    "evidence_sentence_index": 9,
                    "evidence_sentence_text": evidence_text,
                }
            ]
        return output


def _write_compare_files(kb_dir: Path) -> None:
    kb_dir.mkdir(parents=True, exist_ok=True)
    (kb_dir / STANDARD_KB_FILE_NAME).write_text(
        json.dumps({"标准分类": [{"这是正文。": "P"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (kb_dir / TENDER_KB_FILE_NAME).write_text(
        json.dumps({"3.2": [{"这是正文。": "非强制-报价行动-Tutorial-Action"}]}, ensure_ascii=False),
        encoding="utf-8",
    )


def test_compare_stream_returns_sse_events_for_selected_knowledge_bases_in_order(tmp_path: Path) -> None:
    kb_dir = tmp_path / "知识库"
    _write_compare_files(kb_dir)

    app = create_app()
    app.state.knowledge_base_manager = KnowledgeBaseManager(kb_dir)
    app.state.matcher_llm = FakeLLM()
    client = TestClient(app)

    content = "1 总则\n这是正文。\n"
    upload_resp = client.post(
        "/api/v1/documents/upload",
        files={"file": ("demo.md", content.encode("utf-8"), "text/markdown")},
    )
    doc_id = upload_resp.json()["doc_id"]

    with client.stream(
        "POST",
        f"/api/v1/documents/{doc_id}/compare/stream",
        json={"knowledge_base_files": [STANDARD_KB_FILE_NAME, TENDER_KB_FILE_NAME]},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    standard_index = body.index(f'"kb_file":"{STANDARD_KB_FILE_NAME}"')
    tender_index = body.index(f'"kb_file":"{TENDER_KB_FILE_NAME}"')

    assert standard_index < tender_index
    assert '"kb_display_name":"标准化配套知识库"' in body
    assert '"kb_display_name":"投标说明知识库"' in body
    assert '"type_code":"P"' in body
    assert '"type_code":"非强制-报价行动"' in body
    assert '"category":"非强制-报价行动"' in body
    assert '"evidence_sentence_text":"这是正文。"' in body
    assert "event: compare_done" in body


def test_compare_stream_recovers_hits_via_fallback_matching_when_classification_is_empty(tmp_path: Path) -> None:
    kb_dir = tmp_path / "知识库"
    kb_dir.mkdir(parents=True, exist_ok=True)
    (kb_dir / STANDARD_KB_FILE_NAME).write_text(
        json.dumps(
            {
                "分类A": [{"不相关条目": "P"}],
                "分类B": [{"这是正文。": "P"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    app = create_app()
    app.state.knowledge_base_manager = KnowledgeBaseManager(kb_dir)
    app.state.matcher_llm = FallbackRecoveringLLM()
    client = TestClient(app)

    content = "1 总则\n这是正文。\n"
    upload_resp = client.post(
        "/api/v1/documents/upload",
        files={"file": ("demo.md", content.encode("utf-8"), "text/markdown")},
    )
    doc_id = upload_resp.json()["doc_id"]

    with client.stream(
        "POST",
        f"/api/v1/documents/{doc_id}/compare/stream",
        json={"knowledge_base_files": [STANDARD_KB_FILE_NAME]},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    assert '"category":"分类B"' in body
    assert '"reason":"直接支持：fallback recovered"' in body
    assert '"label":"命中"' in body


class FlakyBatchLLM:
    def __init__(self) -> None:
        self.calls = 0

    async def classify_categories_batch(self, *, chunks, category_keys, category_contexts=None):
        return {chunk_id: [category_keys[0]] for chunk_id, _ in chunks}

    async def match_items_batch(self, *, category, entries, chunks):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary upstream failure")

        output = {}
        for chunk in chunks:
            chunk_id = chunk["chunk_id"] if isinstance(chunk, dict) else chunk[0]
            output[chunk_id] = [
                {
                    "entry_id": entries[0].entry_id,
                    "reason": "直接支持：重试后成功",
                    "evidence_sentence_index": 0,
                    "evidence_sentence_text": "这是正文。",
                }
            ]
        return output


class FallbackRecoveringLLM:
    async def classify_categories_batch(self, *, chunks, category_keys, category_contexts=None):
        return {chunk_id: [] for chunk_id, _ in chunks}

    async def match_items_batch(self, *, category, entries, chunks):
        output = {}
        for chunk in chunks:
            chunk_id = chunk["chunk_id"] if isinstance(chunk, dict) else chunk[0]
            output[chunk_id] = []
            if category == "分类B":
                output[chunk_id].append(
                    {
                        "entry_id": entries[0].entry_id,
                        "reason": "直接支持：fallback recovered",
                        "evidence_sentence_index": 0,
                        "evidence_sentence_text": "这是正文。",
                    }
                )
        return output


class ResumeAwareLLM:
    def __init__(self) -> None:
        self.remaining_failures_by_chunk: dict[int, int] = {2: 2}
        self.seen_chunk_ids: list[int] = []

    async def classify_categories_batch(self, *, chunks, category_keys, category_contexts=None):
        return {chunk_id: [category_keys[0]] for chunk_id, _ in chunks}

    async def match_items_batch(self, *, category, entries, chunks):
        output = {}
        for chunk in chunks:
            chunk_id = chunk["chunk_id"] if isinstance(chunk, dict) else chunk[0]
            self.seen_chunk_ids.append(chunk_id)
            if self.remaining_failures_by_chunk.get(chunk_id, 0) > 0:
                self.remaining_failures_by_chunk[chunk_id] -= 1
                raise RuntimeError("chunk 2 failed once")

            output[chunk_id] = [
                {
                    "entry_id": entries[0].entry_id,
                    "reason": f"直接支持：chunk {chunk_id} success",
                    "evidence_sentence_index": 0,
                    "evidence_sentence_text": f"chunk {chunk_id}",
                }
            ]
        return output


def _create_session_with_chunks(client: TestClient) -> str:
    store = client.app.state.session_store
    session = store.create(
        source_file_name="demo.md",
        chunks=[
            Chunk(chunk_id=1, source="demo.md", heading="1 总则", level=1, line_no=1, content="这是正文。"),
            Chunk(chunk_id=2, source="demo.md", heading="1.1 子章节", level=2, line_no=2, content="这是正文。"),
        ],
    )
    return session.doc_id


def test_compare_stream_retries_failed_batch_once_before_emitting_error(tmp_path: Path) -> None:
    kb_dir = tmp_path / "知识库"
    _write_compare_files(kb_dir)

    app = create_app()
    app.state.knowledge_base_manager = KnowledgeBaseManager(kb_dir)
    app.state.matcher_llm = FlakyBatchLLM()
    client = TestClient(app)
    doc_id = _create_session_with_chunks(client)

    with client.stream(
        "POST",
        f"/api/v1/documents/{doc_id}/compare/stream",
        json={"knowledge_base_files": [STANDARD_KB_FILE_NAME]},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    assert body.count("event: error") == 0
    assert body.count("event: chunk_result") == 2
    assert '"failed":0' in body
    assert '"succeeded":2' in body


def test_compare_stream_resume_skips_already_succeeded_chunks(tmp_path: Path) -> None:
    kb_dir = tmp_path / "知识库"
    _write_compare_files(kb_dir)

    app = create_app()
    app.state.knowledge_base_manager = KnowledgeBaseManager(kb_dir)
    llm = ResumeAwareLLM()
    app.state.matcher_llm = llm
    client = TestClient(app)
    doc_id = _create_session_with_chunks(client)

    original_batch_size = compare_routes.BATCH_SIZE
    compare_routes.BATCH_SIZE = 1
    try:
        with client.stream(
            "POST",
            f"/api/v1/documents/{doc_id}/compare/stream",
            json={"knowledge_base_files": [STANDARD_KB_FILE_NAME]},
        ) as first_response:
            assert first_response.status_code == 200
            first_body = "".join(first_response.iter_text())

        assert first_body.count("event: chunk_result") == 1
        assert '"chunk_id":2' in first_body
        assert '"failed":1' in first_body
        assert '"succeeded":1' in first_body

        with client.stream(
            "POST",
            f"/api/v1/documents/{doc_id}/compare/stream",
            json={"knowledge_base_files": [STANDARD_KB_FILE_NAME]},
        ) as second_response:
            assert second_response.status_code == 200
            second_body = "".join(second_response.iter_text())

        assert second_body.count("event: chunk_result") == 1
        assert '"chunk_id":2' in second_body
        assert '"chunk_id":1' not in second_body
        assert '"skipped":1' in second_body
        assert '"failed":0' in second_body
        assert '"succeeded":2' in second_body
        assert llm.seen_chunk_ids == [1, 2, 2, 2]
    finally:
        compare_routes.BATCH_SIZE = original_batch_size

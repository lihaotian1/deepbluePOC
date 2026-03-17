import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.compare_profiles import STANDARD_KB_FILE_NAME, TENDER_KB_FILE_NAME
from app.services.knowledge_base_manager import KnowledgeBaseManager


class FakeLLM:
    async def classify_categories_batch(self, *, chunks, category_keys):
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
                    "reason": "语义一致",
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

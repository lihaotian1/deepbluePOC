from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.splitter_service import SplitterService


def test_upload_and_patch_chunks_flow() -> None:
    app = create_app()
    client = TestClient(app)

    content = "1 总则\n这是正文。\n\n1.1 要求\n这是子章节。\n"
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("demo.md", content.encode("utf-8"), "text/markdown")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["doc_id"]
    assert len(payload["chunks"]) >= 1

    doc_id = payload["doc_id"]
    chunk_id = payload["chunks"][0]["chunk_id"]
    new_text = "# edited\nupdated"
    patch_resp = client.patch(
        f"/api/v1/documents/{doc_id}/chunks",
        json={"chunks": [{"chunk_id": chunk_id, "content": new_text}]},
    )
    assert patch_resp.status_code == 200
    patched = patch_resp.json()
    first_chunk = next(c for c in patched["chunks"] if c["chunk_id"] == chunk_id)
    assert first_chunk["content"] == new_text


def test_review_update_persists_reviewed_results_and_submission_state() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("demo.md", "1 总则\n这是正文。\n".encode("utf-8"), "text/markdown")},
    )
    assert response.status_code == 200
    payload = response.json()

    doc_id = payload["doc_id"]
    chunk = payload["chunks"][0]
    review_response = client.put(
        f"/api/v1/documents/{doc_id}/review",
        json={
            "submitted_for_review": True,
            "compare_results_by_kb": {
                "标准化配套知识库.json": [
                    {
                        "chunk_id": chunk["chunk_id"],
                        "heading": chunk["heading"],
                        "content": chunk["content"],
                        "categories": ["分类A"],
                        "matches": [
                            {
                                "entry_id": "manual-1",
                                "category": "分类A",
                                "text": "人工补充条目",
                                "type_code": "P",
                                "reason": "人工审核意见",
                                "evidence_sentence_index": None,
                                "evidence_sentence_text": "",
                            }
                        ],
                        "label": "命中",
                        "review_status": "已审",
                    }
                ]
            },
        },
    )

    assert review_response.status_code == 200
    review_payload = review_response.json()
    assert review_payload["submitted_for_review"] is True
    assert review_payload["compare_results_by_kb"]["标准化配套知识库.json"][0]["review_status"] == "已审"

    patch_response = client.patch(
        f"/api/v1/documents/{doc_id}/chunks",
        json={"chunks": [{"chunk_id": chunk["chunk_id"], "content": "人工修改后的正文"}]},
    )

    assert patch_response.status_code == 200
    session = app.state.session_store.get(doc_id)
    assert session is not None
    assert session.compare_results_by_kb == {}
    assert session.submitted_for_review is False


def test_upload_tries_gpt_first_and_falls_back_to_engineering_on_gpt_error(tmp_path: Path) -> None:
    calls: list[str] = []

    def fake_extract_text(_path: Path) -> str:
        return "1 heading\nbody"

    def fake_split_with_gpt(*, text: str, source_name: str, api_key: str, base_url: str, model: str, timeout: int):
        calls.append("gpt")
        raise RuntimeError("gpt unavailable")

    def fake_split_with_engineering(text: str, source_name: str):
        calls.append("engineering")
        return [
            {
                "chunk_id": 1,
                "source": source_name,
                "heading": "ENGINEERING FALLBACK",
                "level": 1,
                "line_no": 1,
                "content": "fallback chunk content",
            }
        ]

    app = create_app()
    app.state.splitter_service = SplitterService(
        temp_dir=tmp_path,
        extract_text_fn=fake_extract_text,
        engineering_splitter=fake_split_with_engineering,
        gpt_splitter=fake_split_with_gpt,
        api_key="test-key",
        base_url="https://example.test/v1",
        model="test-model",
        timeout=12,
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("demo.md", b"1 heading\nbody", "text/markdown")},
    )

    assert response.status_code == 200
    assert response.json()["chunks"][0]["heading"] == "ENGINEERING FALLBACK"
    assert calls == ["gpt", "engineering"]

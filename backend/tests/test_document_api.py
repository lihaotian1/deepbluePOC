from fastapi.testclient import TestClient

from app.main import create_app


def test_upload_returns_full_document_text_without_chunks() -> None:
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
    assert payload["source_file_name"] == "demo.md"
    assert payload["document_text"] == content
    assert "chunks" not in payload


def test_review_update_persists_compare_rows_and_submission_state() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("demo.md", "1 总则\n这是正文。\n".encode("utf-8"), "text/markdown")},
    )
    assert response.status_code == 200
    payload = response.json()

    doc_id = payload["doc_id"]
    review_response = client.put(
        f"/api/v1/documents/{doc_id}/review",
        json={
            "submitted_for_review": True,
            "compare_rows": [
                {
                    "row_id": "kb-1::source-1",
                    "chapter_title": "1 总则",
                    "source_excerpt": "这是正文。",
                    "kb_entry_id": "分类A-1",
                    "kb_entry_text": "标准条目原文",
                    "difference_summary": "部分满足：存在语言范围差异，需要与甲方澄清。",
                    "type_code": "P",
                    "review_comment": "人工审核意见",
                    "review_status": "已审",
                }
            ],
        },
    )

    assert review_response.status_code == 200
    review_payload = review_response.json()
    assert review_payload["submitted_for_review"] is True
    assert review_payload["compare_rows"][0]["review_status"] == "已审"
    assert review_payload["compare_rows"][0]["review_comment"] == "人工审核意见"

    session = app.state.session_store.get(doc_id)
    assert session is not None
    assert session.submitted_for_review is True
    assert session.compare_rows[0].difference_summary.startswith("部分满足：")

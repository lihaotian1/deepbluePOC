from app.schemas import CompareRow
from app.services.session_store import SessionStore


def build_row(*, row_id: str, summary: str) -> CompareRow:
    return CompareRow(
        row_id=row_id,
        chapter_title="1 总则",
        source_excerpt="source excerpt",
        kb_entry_id="kb-1",
        kb_entry_text="标准条目",
        difference_summary=summary,
        type_code="P",
        review_comment="",
        review_status="未审",
    )


def test_create_session_stores_full_document_text() -> None:
    store = SessionStore()
    session = store.create(
        source_file_name="demo.md",
        document_text="1 总则\n这是正文。\n",
    )

    assert session.source_file_name == "demo.md"
    assert session.document_text == "1 总则\n这是正文。\n"
    assert session.compare_rows == []


def test_save_compare_rows_replaces_previous_rows_and_resets_submission_state() -> None:
    store = SessionStore()
    session = store.create(
        source_file_name="demo.md",
        document_text="1 总则\n这是正文。\n",
    )

    saved = store.save_compare_rows(
        session.doc_id,
        [
            build_row(row_id="row-1", summary="直接满足：标准条目可直接满足甲方要求。"),
        ],
    )

    assert saved is not None
    assert len(saved.compare_rows) == 1
    assert saved.submitted_for_review is False

    reviewed = store.save_review_state(
        session.doc_id,
        compare_rows=[
            build_row(row_id="row-2", summary="部分满足：需要向甲方澄清。").model_copy(
                update={"review_status": "已审", "review_comment": "已审核"}
            )
        ],
        submitted_for_review=True,
    )

    assert reviewed is not None
    assert reviewed.submitted_for_review is True
    assert reviewed.compare_rows[0].row_id == "row-2"
    assert reviewed.compare_rows[0].review_status == "已审"

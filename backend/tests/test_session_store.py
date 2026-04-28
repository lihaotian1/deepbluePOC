from app.schemas import CompareAnalysisResult, CompareRow, OtherRequirementRow
from app.services.session_store import SessionStore


def build_row(*, row_id: str, summary: str) -> CompareRow:
    return CompareRow(
        row_id=row_id,
        chapter_title="1 总则",
        source_excerpt="source excerpt",
        kb_entry_id="kb-1",
        kb_entry_text="标准条目",
        difference_summary_brief="一句话总结",
        difference_summary=summary,
        type_code="P",
        review_comment="",
        review_status="未审",
    )


def build_other_requirement(*, row_id: str, source_excerpt: str) -> OtherRequirementRow:
    return OtherRequirementRow(
        row_id=row_id,
        chapter_title="3 参数",
        source_excerpt=source_excerpt,
        summary="询价文件要求提供额外技术参数。",
        source_order=2,
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
    assert session.other_requirements == []


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


def test_save_compare_analysis_persists_other_requirements_and_review_state_preserves_them() -> None:
    store = SessionStore()
    session = store.create(
        source_file_name="demo.md",
        document_text="1 总则\n这是正文。\n",
    )

    saved = store.save_compare_analysis(
        session.doc_id,
        compare_rows=[build_row(row_id="row-1", summary="直接满足：标准条目可直接满足甲方要求。")],
        other_requirements=[build_other_requirement(row_id="other-1", source_excerpt="Pump flow shall be 120 m3/h.")],
    )

    assert saved is not None
    assert len(saved.compare_rows) == 1
    assert len(saved.other_requirements) == 1
    assert saved.other_requirements[0].row_id == "other-1"

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
    assert reviewed.other_requirements[0].source_excerpt == "Pump flow shall be 120 m3/h."


def test_compare_cache_roundtrip_returns_independent_row_copies() -> None:
    store = SessionStore()
    analysis = CompareAnalysisResult(
        compare_rows=[build_row(row_id="row-1", summary="直接满足：标准条目可直接满足甲方要求。")],
        other_requirements=[build_other_requirement(row_id="other-1", source_excerpt="Pump flow shall be 120 m3/h.")],
    )

    store.save_compare_cache("cache-key", analysis)
    cached = store.get_compare_cache("cache-key")

    assert cached is not None
    assert len(cached.compare_rows) == 1
    assert len(cached.other_requirements) == 1
    assert cached.compare_rows[0].row_id == "row-1"
    cached.compare_rows[0].review_comment = "changed"
    cached.other_requirements[0].summary = "changed"

    cached_again = store.get_compare_cache("cache-key")
    assert cached_again is not None
    assert cached_again.compare_rows[0].review_comment == ""
    assert cached_again.other_requirements[0].summary == "询价文件要求提供额外技术参数。"

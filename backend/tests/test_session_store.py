from app.schemas import Chunk, ChunkCompareResult, MatchItem
from app.services.session_store import SessionStore


def build_chunk(*, chunk_id: int, content: str) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        source="demo.md",
        heading=f"Chunk {chunk_id}",
        level=1,
        line_no=chunk_id,
        content=content,
    )


def build_result(*, chunk_id: int, content: str) -> ChunkCompareResult:
    return ChunkCompareResult(
        chunk_id=chunk_id,
        heading=f"Chunk {chunk_id}",
        content=content,
        categories=["分类A"],
        matches=[
            MatchItem(
                entry_id="kb-1",
                category="分类A",
                text="符合 API 610",
                type_code="P",
                reason="命中原句",
                evidence_sentence_index=0,
                evidence_sentence_text=content,
            )
        ],
        label="命中",
    )


def test_update_chunks_clears_saved_compare_results() -> None:
    store = SessionStore()
    session = store.create(
        source_file_name="demo.md",
        chunks=[build_chunk(chunk_id=1, content="original"), build_chunk(chunk_id=2, content="second")],
    )

    saved = store.save_results(
        session.doc_id,
        "标准化配套知识库.json",
        [build_result(chunk_id=1, content="original")],
    )

    assert saved is not None
    assert list(saved.compare_results_by_kb) == ["标准化配套知识库.json"]
    assert len(saved.compare_results_by_kb["标准化配套知识库.json"]) == 1

    updated = store.update_chunks(session.doc_id, {1: "edited"})

    assert updated is not None
    assert updated.chunks[0].content == "edited"
    assert updated.chunks[1].content == "second"
    assert updated.compare_results_by_kb == {}
    assert store.get(session.doc_id) is not None
    assert store.get(session.doc_id).compare_results_by_kb == {}


def test_save_results_tracks_each_knowledge_base_separately() -> None:
    store = SessionStore()
    session = store.create(
        source_file_name="demo.md",
        chunks=[build_chunk(chunk_id=1, content="original")],
    )

    standard_saved = store.save_results(
        session.doc_id,
        "标准化配套知识库.json",
        [build_result(chunk_id=1, content="original")],
    )
    tender_saved = store.save_results(
        session.doc_id,
        "投标说明知识库.json",
        [build_result(chunk_id=1, content="original")],
    )

    assert standard_saved is not None
    assert tender_saved is not None
    assert set(tender_saved.compare_results_by_kb) == {"标准化配套知识库.json", "投标说明知识库.json"}
    assert len(tender_saved.compare_results_by_kb["标准化配套知识库.json"]) == 1
    assert len(tender_saved.compare_results_by_kb["投标说明知识库.json"]) == 1

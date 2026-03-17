from io import BytesIO

from openpyxl import load_workbook

from app.schemas import Chunk, ChunkCompareResult, MatchItem
from app.services.export_service import build_export_workbook


EXPECTED_HEADERS = (
    "序号",
    "询价文件章节标题",
    "询价文件章节原文",
    "标准偏差类型",
    "标准偏差原文",
    "标准偏差分类",
)


def _load_first_sheet_rows(blob: bytes) -> list[tuple[object, ...]]:
    workbook = load_workbook(BytesIO(blob))
    sheet = workbook.worksheets[0]
    return list(sheet.iter_rows(values_only=True))


def test_export_workbook_writes_expected_headers_and_matched_row() -> None:
    chunks = [
        Chunk(chunk_id=7, source="demo.pdf", heading="1.1", level=2, line_no=1, content="content 1"),
    ]
    results = [
        ChunkCompareResult(
            chunk_id=7,
            heading="1.1",
            content="content 1",
            categories=["分类A"],
            matches=[
                MatchItem(
                    entry_id="A-1",
                    category="分类A",
                    text="符合API 610",
                    type_code="P",
                    reason="语义一致",
                )
            ],
            label="命中",
        )
    ]

    rows = _load_first_sheet_rows(build_export_workbook(chunks=chunks, results=results))

    assert rows[0] == EXPECTED_HEADERS
    assert rows[1] == (1, "1.1", "content 1", "分类A", "符合API 610", "P")
    assert len(rows) == 2


def test_export_workbook_writes_other_row_for_unmatched_chunk() -> None:
    chunks = [
        Chunk(chunk_id=42, source="demo.pdf", heading="2.3", level=2, line_no=9, content="content 2"),
    ]
    results = [
        ChunkCompareResult(
            chunk_id=42,
            heading="2.3",
            content="content 2",
            categories=[],
            matches=[],
            label="其他",
        )
    ]

    rows = _load_first_sheet_rows(build_export_workbook(chunks=chunks, results=results))

    assert rows[0] == EXPECTED_HEADERS
    assert rows[1] == (1, "2.3", "content 2", None, None, "OTHER")
    assert len(rows) == 2


def test_export_workbook_preserves_chunk_order_for_missing_result_fallback() -> None:
    chunks = [
        Chunk(chunk_id=1, source="demo.pdf", heading="1.1", level=2, line_no=1, content="content 1"),
        Chunk(chunk_id=2, source="demo.pdf", heading="1.2", level=2, line_no=2, content="content 2"),
    ]
    results = [
        ChunkCompareResult(
            chunk_id=2,
            heading="1.2",
            content="content 2",
            categories=["分类B"],
            matches=[
                MatchItem(
                    entry_id="B-1",
                    category="分类B",
                    text="符合GB/T 123",
                    type_code="B",
                    reason="语义一致",
                )
            ],
            label="命中",
        )
    ]

    rows = _load_first_sheet_rows(build_export_workbook(chunks=chunks, results=results))

    assert rows[0] == EXPECTED_HEADERS
    assert rows[1] == (1, "1.1", "content 1", None, None, "OTHER")
    assert rows[2] == (2, "1.2", "content 2", "分类B", "符合GB/T 123", "B")
    assert len(rows) == 3

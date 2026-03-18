from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from app.schemas import Chunk, ChunkCompareResult


HEADERS = [
    "序号",
    "询价文件章节标题",
    "询价文件章节原文",
    "标准偏差类型",
    "标准偏差原文",
    "标准偏差分类",
    "审核意见",
    "审核状态",
]


def build_export_workbook(
    *,
    chunks: list[Chunk],
    results_by_kb: dict[str, list[ChunkCompareResult]],
    sheet_names_by_kb: dict[str, str],
) -> bytes:
    workbook = Workbook()
    result_sheet = workbook.active
    assert result_sheet is not None
    first_sheet = True

    for kb_file, results in results_by_kb.items():
        sheet = result_sheet if first_sheet else workbook.create_sheet()
        first_sheet = False
        _populate_result_sheet(
            sheet=sheet,
            chunks=chunks,
            results=results,
            title=sheet_names_by_kb.get(kb_file, kb_file.removesuffix(".json")),
        )

    if not results_by_kb:
        _populate_result_sheet(sheet=result_sheet, chunks=chunks, results=[], title="results")

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _populate_result_sheet(
    *,
    sheet: Worksheet,
    chunks: list[Chunk],
    results: list[ChunkCompareResult],
    title: str,
) -> None:
    sheet.title = title
    sheet.append(HEADERS)

    exported_rows: list[list[str | int | None]] = []
    result_map = {row.chunk_id: row for row in results}

    for chunk in chunks:
        row = result_map.get(chunk.chunk_id)
        if row is None or not row.matches:
            review_status = row.review_status if row is not None else "未审"
            exported_rows.append([chunk.heading, chunk.content, None, None, "OTHER", None, review_status])
            continue

        for match in row.matches:
            exported_rows.append([chunk.heading, chunk.content, match.category, match.text, match.type_code, match.reason or None, row.review_status])

    chunk_ids = {chunk.chunk_id for chunk in chunks}
    for row in results:
        if row.chunk_id in chunk_ids:
            continue

        if not row.matches:
            exported_rows.append([row.heading, row.content, None, None, "OTHER", None, row.review_status])
            continue

        for match in row.matches:
            exported_rows.append([row.heading, row.content, match.category, match.text, match.type_code, match.reason or None, row.review_status])

    for index, row in enumerate(exported_rows, start=1):
        sheet.append([index, *row])

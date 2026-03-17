from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook

from app.schemas import Chunk, ChunkCompareResult


def build_export_workbook(*, chunks: list[Chunk], results: list[ChunkCompareResult]) -> bytes:
    workbook = Workbook()
    result_sheet = workbook.active
    assert result_sheet is not None
    result_sheet.title = "results"
    result_sheet.append(
        [
            "序号",
            "询价文件章节标题",
            "询价文件章节原文",
            "标准偏差类型",
            "标准偏差原文",
            "标准偏差分类",
        ]
    )

    exported_rows: list[list[str | int | None]] = []
    result_map = {row.chunk_id: row for row in results}

    for chunk in chunks:
        row = result_map.get(chunk.chunk_id)
        if row is None or not row.matches:
            exported_rows.append([chunk.heading, chunk.content, None, None, "OTHER"])
            continue

        for match in row.matches:
            exported_rows.append([chunk.heading, chunk.content, match.category, match.text, match.type_code])

    chunk_ids = {chunk.chunk_id for chunk in chunks}
    for row in results:
        if row.chunk_id in chunk_ids:
            continue

        if not row.matches:
            exported_rows.append([row.heading, row.content, None, None, "OTHER"])
            continue

        for match in row.matches:
            exported_rows.append([row.heading, row.content, match.category, match.text, match.type_code])

    for index, row in enumerate(exported_rows, start=1):
        result_sheet.append([index, *row])

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()

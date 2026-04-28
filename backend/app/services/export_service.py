from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from app.schemas import CompareRow, OtherRequirementRow


HEADERS = [
    "序号",
    "章节标题",
    "询价文件原文段落或句子",
    "知识库标准化配套条目的原文",
    "差异结论",
    "详细差异说明",
    "分类",
    "审核意见",
    "审核状态",
]

OTHER_REQUIREMENT_HEADERS = [
    "序号",
    "询价文件最小原文",
    "AI一句话总结",
]

def build_export_workbook(
    *,
    rows: list[CompareRow],
    other_requirements: list[OtherRequirementRow] | None = None,
    title: str,
) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    _populate_result_sheet(sheet=sheet, rows=rows, title=title)
    other_sheet = workbook.create_sheet("其他要求")
    _populate_other_requirement_sheet(sheet=other_sheet, rows=other_requirements or [])

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _populate_result_sheet(*, sheet: Worksheet, rows: list[CompareRow], title: str) -> None:
    sheet.title = title
    sheet.append(HEADERS)

    for index, row in enumerate(rows, start=1):
        sheet.append(
            [
                index,
                row.chapter_title,
                row.source_excerpt,
                row.kb_entry_text,
                row.difference_summary_brief,
                row.difference_summary,
                row.type_code,
                row.review_comment or None,
                row.review_status,
            ]
        )


def _populate_other_requirement_sheet(*, sheet: Worksheet, rows: list[OtherRequirementRow]) -> None:
    sheet.append(OTHER_REQUIREMENT_HEADERS)

    for index, row in enumerate(sorted(rows, key=lambda item: item.source_order), start=1):
        sheet.append(
            [
                index,
                row.source_excerpt,
                row.summary,
            ]
        )

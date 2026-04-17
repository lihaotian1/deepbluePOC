from io import BytesIO

from openpyxl import load_workbook

from app.schemas import CompareRow
from app.services.export_service import build_export_workbook


EXPECTED_HEADERS = (
    "序号",
    "章节标题",
    "询价文件原文段落或句子",
    "知识库标准化配套条目的原文",
    "差异结论",
    "详细差异说明",
    "分类",
    "审核意见",
    "审核状态",
)


def _load_first_sheet_rows(blob: bytes) -> list[tuple[object, ...]]:
    workbook = load_workbook(BytesIO(blob))
    sheet = workbook.worksheets[0]
    return list(sheet.iter_rows(values_only=True))


def test_export_workbook_writes_expected_headers_and_compare_rows() -> None:
    rows = [
        CompareRow(
            row_id="row-1",
            chapter_title="6 DOCUMENTATION",
            source_excerpt="Vendor shall provide the appendices in Russian and English.",
            kb_entry_id="General Specification-12",
            kb_entry_text="产品资料仅提供中英文版本。",
            difference_summary_brief="文件语言要求超出我方标准范围。",
            difference_summary="存在冲突：甲方要求附录提供俄语和英语版本，而我方标准仅支持中英文，需要与甲方澄清。",
            type_code="P",
            review_comment="已提醒销售澄清语言范围。",
            review_status="已审",
        )
    ]

    exported_rows = _load_first_sheet_rows(build_export_workbook(rows=rows, title="标准化配套结果"))

    assert exported_rows[0] == EXPECTED_HEADERS
    assert exported_rows[1] == (
        1,
        "6 DOCUMENTATION",
        "Vendor shall provide the appendices in Russian and English.",
        "产品资料仅提供中英文版本。",
        "文件语言要求超出我方标准范围。",
        "存在冲突：甲方要求附录提供俄语和英语版本，而我方标准仅支持中英文，需要与甲方澄清。",
        "P",
        "已提醒销售澄清语言范围。",
        "已审",
    )
    assert len(exported_rows) == 2


def test_export_workbook_does_not_append_other_rows_for_unmatched_content() -> None:
    rows = []

    exported_rows = _load_first_sheet_rows(build_export_workbook(rows=rows, title="标准化配套结果"))

    assert exported_rows[0] == EXPECTED_HEADERS
    assert len(exported_rows) == 1

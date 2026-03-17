from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from chapter_splitter import (
    _build_gpt_messages,
    _detect_headings,
    split_text_engineering,
    split_text_with_gpt,
)


SAMPLE_TEXT = """
5 总则
这里是 5 章总述。

5.1 设计要求
这里是 5.1 章引言。

5.1.1 机械密封
机械密封的正文。

5.1.2 轴承
轴承的正文。

6 试验与验收
6 章没有子章节，因此应该整体保留。

附件A 备件清单
附件内容。
""".strip()


def test_engineering_split_uses_smallest_sections():
    chunks = split_text_engineering(SAMPLE_TEXT, source_name="demo.txt")
    headings = [chunk["heading"] for chunk in chunks]

    assert "5 总则" not in headings
    assert "5.1 设计要求" not in headings
    assert "5.1.1 机械密封" in headings
    assert "5.1.2 轴承" in headings
    assert "6 试验与验收" in headings
    assert "附件A 备件清单" in headings


def test_engineering_split_handles_page_prefix_heading():
    text = """
    Page 4 of 57 1 GENERAL
    第一章正文。
    1.1 SCOPE
    子章节正文。
    """.strip()

    chunks = split_text_engineering(text, source_name="page_prefix.txt")
    headings = [chunk["heading"] for chunk in chunks]

    assert "1 GENERAL" not in headings
    assert "1.1 SCOPE" in headings


def test_gpt_split_falls_back_to_min_leaf_when_model_returns_parents():
    def fake_request_fn(api_key, model, messages, timeout) -> dict[str, object]:
        assert "最小章节" in messages[0]["content"]
        return {"keep_indices": [0, 1, 2, 3, 4, 5]}

    chunks = split_text_with_gpt(
        SAMPLE_TEXT,
        api_key="test-key",
        source_name="demo.txt",
        request_fn=fake_request_fn,
    )
    headings = [chunk["heading"] for chunk in chunks]

    assert "5 总则" not in headings
    assert "5.1 设计要求" not in headings
    assert "5.1.1 机械密封" in headings
    assert "5.1.2 轴承" in headings
    assert "6 试验与验收" in headings
    assert "附件A 备件清单" in headings


def test_gpt_split_rejects_skipping_existing_intermediate_headings():
    text = """
    1.7 Existing heading
    text for 1.7.

    1.8 Existing intermediate heading
    text for 1.8.

    1.9 Next heading
    text for 1.9.
    """.strip()

    def fake_request_fn(api_key, model, messages, timeout) -> dict[str, object]:
        return {"keep_indices": [0, 2]}

    chunks = split_text_with_gpt(
        text,
        api_key="test-key",
        source_name="intermediate.txt",
        request_fn=fake_request_fn,
    )
    headings = [chunk["heading"] for chunk in chunks]

    assert "1.7 Existing heading" in headings
    assert "1.8 Existing intermediate heading" in headings
    assert "1.9 Next heading" in headings


def test_gpt_messages_explicitly_forbid_skipping_existing_intermediate_headings():
    text = """
    1.7 Existing heading
    text for 1.7.

    1.8 Existing intermediate heading
    text for 1.8.

    1.9 Next heading
    text for 1.9.
    """.strip()

    messages = _build_gpt_messages(_detect_headings(text))
    system_prompt = messages[0]["content"]

    assert "中间编号章节" in system_prompt
    assert "不得跳过" in system_prompt


def test_engineering_split_preserves_existing_intermediate_numeric_heading():
    skipped_heading = (
        "1.8 RECOMMENDED DESIGN AND INSTALLATION REQUIREMENTS FOR CONTROL VALVES "
        "IN HIGH PRESSURE STEAM AND CONDENSATE SERVICE LINES WITH FLEXIBLE "
        "BYPASS ARRANGEMENTS AND REMOTE OPERATION POINTS"
    )
    text = f"""
    1.7 GENERAL REQUIREMENTS
    text for 1.7.

    {skipped_heading}
    text for 1.8.

    1.9 NEXT REQUIREMENTS
    text for 1.9.
    """.strip()

    detected_headings = [heading.text for heading in _detect_headings(text)]
    chunks = split_text_engineering(text, source_name="regression.txt")
    chunk_headings = [chunk["heading"] for chunk in chunks]

    assert skipped_heading in detected_headings
    assert skipped_heading in chunk_headings

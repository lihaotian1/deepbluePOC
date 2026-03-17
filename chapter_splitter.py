from __future__ import annotations

import argparse
import inspect
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

import requests


SUPPORTED_SUFFIXES = {".txt", ".md", ".pdf", ".docx"}


@dataclass(frozen=True)
class Heading:
    index: int
    text: str
    level: int
    line_no: int
    start_char: int
    kind: str


def extract_text_from_file(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return _read_text_file(file_path)
    if suffix == ".pdf":
        return _extract_text_from_pdf(file_path)
    if suffix == ".docx":
        return _extract_text_from_docx(file_path)
    raise ValueError(f"Unsupported file type: {file_path}")


def split_text_engineering(text: str, source_name: str = "") -> List[Dict[str, object]]:
    normalized_text = _normalize_text(text)
    headings = _detect_headings(normalized_text)
    if not headings:
        return [_build_fallback_chunk(normalized_text, source_name)]

    leaf_indices = _rule_leaf_indices(headings)
    return _build_chunks(normalized_text, headings, leaf_indices, source_name)


def split_text_with_gpt(
    text: str,
    api_key: str,
    source_name: str = "",
    base_url: str = "https://api.openai.com/v1",
    model: str = "gpt-4.1-mini",
    timeout: int = 120,
    request_fn: Optional[Callable[..., Dict[str, object]]] = None,
) -> List[Dict[str, object]]:
    normalized_text = _normalize_text(text)
    headings = _detect_headings(normalized_text)
    if not headings:
        return [_build_fallback_chunk(normalized_text, source_name)]

    selected_indices = _select_leaf_indices_with_gpt(
        headings=headings,
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout=timeout,
        request_fn=request_fn,
    )
    rule_leaf_set = set(_rule_leaf_indices(headings))
    final_leaf_indices = [idx for idx in selected_indices if idx in rule_leaf_set]
    if not final_leaf_indices:
        final_leaf_indices = sorted(rule_leaf_set)

    return _build_chunks(normalized_text, headings, final_leaf_indices, source_name)


def split_input_folder_engineering(
    input_dir: str = "data/input",
    output_dir: str = "data/output/engineering",
) -> List[Path]:
    return _split_input_folder(
        input_dir=input_dir,
        output_dir=output_dir,
        method_name="engineering",
        splitter=lambda text, source_name: split_text_engineering(text, source_name=source_name),
    )


def split_input_folder_with_gpt(
    api_key: str,
    input_dir: str = "data/input",
    output_dir: str = "data/output/gpt",
    base_url: str = "https://api.openai.com/v1",
    model: str = "gpt-4.1-mini",
    timeout: int = 120,
) -> List[Path]:
    return _split_input_folder(
        input_dir=input_dir,
        output_dir=output_dir,
        method_name="gpt",
        splitter=lambda text, source_name: split_text_with_gpt(
            text=text,
            api_key=api_key,
            source_name=source_name,
            base_url=base_url,
            model=model,
            timeout=timeout,
        ),
    )


def _split_input_folder(
    input_dir: str,
    output_dir: str,
    method_name: str,
    splitter: Callable[[str, str], List[Dict[str, object]]],
) -> List[Path]:
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    written_files: List[Path] = []
    for file_path in _iter_input_files(input_path):
        text = extract_text_from_file(file_path)
        chunks = splitter(text, file_path.name)
        payload = {
            "source_file": str(file_path),
            "method": method_name,
            "chunk_count": len(chunks),
            "chunks": chunks,
        }
        out_file = output_path / f"{file_path.stem}_{method_name}_chunks.json"
        out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        written_files.append(out_file)
    return written_files


def _iter_input_files(input_dir: Path) -> List[Path]:
    if not input_dir.exists():
        return []
    files = [
        path
        for path in sorted(input_dir.rglob("*"))
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    ]
    return files


def _read_text_file(file_path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return file_path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return file_path.read_text(encoding="latin-1", errors="ignore")


def _extract_text_from_pdf(file_path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ImportError("Please install pypdf: pip install pypdf") from exc

    reader = PdfReader(str(file_path))
    pages: List[str] = []
    for idx, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        pages.append(f"\n<<<PAGE {idx}>>>\n{page_text}")
    return "\n".join(pages)


def _extract_text_from_docx(file_path: Path) -> str:
    try:
        from docx import Document
    except ImportError as exc:
        raise ImportError("Please install python-docx: pip install python-docx") from exc

    doc = Document(str(file_path))
    return "\n".join(paragraph.text for paragraph in doc.paragraphs)


def _normalize_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\u3000", " ")
    return normalized


def _detect_headings(text: str) -> List[Heading]:
    lines = text.split("\n")
    line_offsets: List[int] = []
    cursor = 0
    for line in lines:
        line_offsets.append(cursor)
        cursor += len(line) + 1

    headings: List[Heading] = []
    for line_no, raw_line in enumerate(lines, start=1):
        cleaned = _clean_line(raw_line)
        if not cleaned or _looks_like_toc_entry(cleaned):
            continue

        parsed = _parse_heading(cleaned)
        if not parsed:
            continue

        heading_text, level, kind = parsed
        headings.append(
            Heading(
                index=len(headings),
                text=heading_text,
                level=level,
                line_no=line_no,
                start_char=line_offsets[line_no - 1],
                kind=kind,
            )
        )

    return headings


def _clean_line(line: str) -> str:
    line = line.replace("\t", " ").strip()
    line = re.sub(r"^\s*Page\s+\d+\s+of\s+\d+\s+", "", line, flags=re.IGNORECASE)
    line = re.sub(r"\s+", " ", line)
    return line.strip()


def _looks_like_toc_entry(line: str) -> bool:
    return bool(re.search(r"\.{2,}\s*\d+\s*$", line))


def _parse_heading(line: str) -> Optional[tuple[str, int, str]]:
    appendix = _parse_appendix_heading(line)
    if appendix:
        return appendix

    chapter_match = re.match(
        r"^第\s*([一二三四五六七八九十百零〇0-9]+)\s*章\s*(.*)$",
        line,
    )
    if chapter_match:
        tail = chapter_match.group(2).strip()
        if not _is_chapter_heading_candidate(tail):
            return None
        text = f"第{chapter_match.group(1)}章"
        if tail:
            text = f"{text} {tail}"
        return text, 1, "chapter"

    numeric_match = re.match(r"^(\d+(?:\.\d+){0,5})\s+(.+)$", line)
    if numeric_match:
        chapter_no = numeric_match.group(1)
        title = numeric_match.group(2).strip()
        if _is_numeric_heading_candidate(chapter_no, title):
            level = chapter_no.count(".") + 1
            return f"{chapter_no} {title}", level, "numeric"

    return None


def _is_numeric_heading_candidate(chapter_no: str, title: str) -> bool:
    if not title:
        return False
    if len(title) > 240:
        return False
    if title.count(",") + title.count(";") > 2:
        return False
    if _has_sentence_punctuation(title):
        return False
    word_count = len(title.split())
    if word_count > 30:
        return False
    if (len(title) > 160 or word_count > 18) and not _looks_like_emphasized_heading(title):
        return False
    first_part = int(chapter_no.split(".")[0])
    if first_part > 100:
        return False

    first_alpha = re.search(r"[A-Za-z]", title)
    if first_alpha and first_alpha.group(0).islower():
        return False
    return True


def _looks_like_emphasized_heading(title: str) -> bool:
    letters = [char for char in title if char.isalpha()]
    if not letters:
        return False
    uppercase_count = sum(1 for char in letters if char.isupper())
    return uppercase_count / len(letters) >= 0.7


def _parse_appendix_heading(line: str) -> Optional[tuple[str, int, str]]:
    prefixes = ("附件", "附录", "ANNEX", "Annex", "APPENDIX", "Appendix", "ATTACHMENT", "Attachment")
    matched_prefix = next((prefix for prefix in prefixes if line.startswith(prefix)), None)
    if not matched_prefix:
        return None

    if len(line) > len(matched_prefix):
        next_char = line[len(matched_prefix)]
        if (
            not next_char.isspace()
            and next_char not in ":：、.-"
            and not re.match(r"[A-Za-z0-9一二三四五六七八九十甲乙丙丁]", next_char)
        ):
            return None

    appendix_match = re.match(
        r"^(附件|附录|ANNEX|Annex|APPENDIX|Appendix|ATTACHMENT|Attachment)"
        r"(?:\s*([A-Za-z0-9一二三四五六七八九十甲乙丙丁]+))?"
        r"(?:\s*[:：、.\-]?\s*(.*))?$",
        line,
    )
    if not appendix_match:
        return None

    suffix = appendix_match.group(2) or ""
    tail = (appendix_match.group(3) or "").strip()
    if not _is_appendix_heading_candidate(tail):
        return None

    prefix = appendix_match.group(1)
    base = f"{prefix}{suffix}" if suffix else prefix
    text = f"{base} {tail}".strip() if tail else base
    return text, 1, "appendix"


def _is_chapter_heading_candidate(tail: str) -> bool:
    if not tail:
        return True
    if len(tail) > 80:
        return False
    if _has_sentence_punctuation(tail):
        return False
    return True


def _is_appendix_heading_candidate(tail: str) -> bool:
    if not tail:
        return True
    if len(tail) > 80:
        return False
    if _has_sentence_punctuation(tail):
        return False
    return True


def _has_sentence_punctuation(text: str) -> bool:
    return any(symbol in text for symbol in ("。", "，", "；", "!", "?", "！", "？"))


def _rule_leaf_indices(headings: List[Heading]) -> List[int]:
    if not headings:
        return []

    leaf_indices: List[int] = []
    for idx, heading in enumerate(headings):
        if idx == len(headings) - 1:
            leaf_indices.append(idx)
            continue
        if headings[idx + 1].level <= heading.level:
            leaf_indices.append(idx)
    return leaf_indices


def _build_chunks(
    text: str,
    headings: List[Heading],
    leaf_indices: List[int],
    source_name: str,
) -> List[Dict[str, object]]:
    leaf_set = set(leaf_indices)
    chunk_parts: Dict[int, List[str]] = {idx: [] for idx in leaf_indices}

    for idx, heading in enumerate(headings):
        start = heading.start_char
        end = headings[idx + 1].start_char if idx + 1 < len(headings) else len(text)
        segment = text[start:end].strip()
        if not segment:
            continue

        if idx in leaf_set:
            chunk_parts[idx].append(segment)
            continue

        target = _first_descendant_leaf(idx, headings, leaf_set)
        if target is not None:
            chunk_parts[target].append(segment)

    chunks: List[Dict[str, object]] = []
    for order, idx in enumerate(sorted(leaf_indices), start=1):
        heading = headings[idx]
        content = "\n\n".join(part for part in chunk_parts[idx] if part.strip()).strip()
        if not content:
            content = heading.text
        chunks.append(
            {
                "chunk_id": order,
                "source": source_name,
                "heading": heading.text,
                "level": heading.level,
                "line_no": heading.line_no,
                "content": content,
            }
        )
    return chunks


def _first_descendant_leaf(
    idx: int,
    headings: List[Heading],
    leaf_set: set[int],
) -> Optional[int]:
    base_level = headings[idx].level
    for cursor in range(idx + 1, len(headings)):
        if headings[cursor].level <= base_level:
            break
        if cursor in leaf_set:
            return cursor
    return None


def _build_fallback_chunk(text: str, source_name: str) -> Dict[str, object]:
    return {
        "chunk_id": 1,
        "source": source_name,
        "heading": "FULL_DOCUMENT",
        "level": 0,
        "line_no": 1,
        "content": text.strip(),
    }


def _select_leaf_indices_with_gpt(
    headings: List[Heading],
    api_key: str,
    base_url: str,
    model: str,
    timeout: int,
    request_fn: Optional[Callable[..., Dict[str, object]]] = None,
) -> List[int]:
    default_leaf = _rule_leaf_indices(headings)
    if not headings:
        return default_leaf

    messages = _build_gpt_messages(headings)
    call = request_fn or _default_openai_request
    request_kwargs = {
        "api_key": api_key,
        "model": model,
        "messages": messages,
        "timeout": timeout,
    }
    parameters = inspect.signature(call).parameters
    if "base_url" in parameters or any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()
    ):
        request_kwargs["base_url"] = base_url

    try:
        result = call(**request_kwargs)
    except Exception:
        return default_leaf

    if isinstance(result, str):
        try:
            result = json.loads(result)
        except json.JSONDecodeError:
            return default_leaf

    if not isinstance(result, dict):
        return default_leaf

    keep_indices = result.get("keep_indices")
    if not isinstance(keep_indices, list):
        return default_leaf

    valid = sorted({idx for idx in keep_indices if isinstance(idx, int) and 0 <= idx < len(headings)})
    if not valid:
        return default_leaf
    if not _keeps_existing_intermediate_numeric_headings(headings, valid):
        return default_leaf
    return valid


def _build_gpt_messages(headings: List[Heading]) -> List[Dict[str, str]]:
    system_prompt = (
        "你是文档切分助手。任务是按最小章节选择应保留的标题索引。\n"
        "规则：\n"
        "1) 只保留最小章节：若父章节有子章节，父章节不要保留。\n"
        "2) 如果章节没有子章节，则保留该章节。\n"
        "3) 附件/附录/Appendix/Annex/Attachment 标题必须纳入判断并保留到最小层级。\n"
        "4) 对于同级数字章节，如果输入里已经存在中间编号章节，则不得跳过；例如已有 1.7、1.8、1.9 时，必须同时保留 1.8。\n"
        "5) 只返回 JSON 对象，格式必须是 {\"keep_indices\": [int, ...]}，索引升序且不重复。\n"
        "6) 只能使用输入里出现的 index，禁止编造。"
    )

    payload = {
        "candidates": [
            {
                "index": heading.index,
                "heading": heading.text,
                "level": heading.level,
                "kind": heading.kind,
            }
            for heading in headings
        ]
    }
    user_prompt = "候选章节如下，请返回 keep_indices：\n" + json.dumps(payload, ensure_ascii=False, indent=2)

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _keeps_existing_intermediate_numeric_headings(headings: List[Heading], selected_indices: List[int]) -> bool:
    selected_set = set(selected_indices)
    sibling_groups: Dict[tuple[int, ...], List[tuple[int, int]]] = {}

    for heading in headings:
        numeric_parts = _parse_numeric_heading_parts(heading)
        if numeric_parts is None:
            continue
        parent_key = numeric_parts[:-1]
        sibling_groups.setdefault(parent_key, []).append((numeric_parts[-1], heading.index))

    for siblings in sibling_groups.values():
        ordered = sorted(siblings)
        selected_positions = [position for position, (_, index) in enumerate(ordered) if index in selected_set]
        if len(selected_positions) < 2:
            continue
        start = selected_positions[0]
        end = selected_positions[-1]
        for _, index in ordered[start : end + 1]:
            if index not in selected_set:
                return False
    return True


def _parse_numeric_heading_parts(heading: Heading) -> tuple[int, ...] | None:
    if heading.kind != "numeric":
        return None
    chapter_no, _, _ = heading.text.partition(" ")
    if not chapter_no:
        return None
    return tuple(int(part) for part in chapter_no.split("."))


def _default_openai_request(
    api_key: str,
    base_url: str,
    model: str,
    messages: List[Dict[str, str]],
    timeout: int,
) -> Dict[str, object]:
    url = f"{base_url.rstrip('/')}/chat/completions"
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "temperature": 0,
            "messages": messages,
            "response_format": {"type": "json_object"},
        },
        timeout=timeout,
    )
    response.raise_for_status()

    data = response.json()
    content = data["choices"][0]["message"]["content"]
    if isinstance(content, list):
        text = "".join(item.get("text", "") for item in content if isinstance(item, dict))
    else:
        text = content
    return json.loads(text)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Split files in data/input into smallest chapter chunks.")
    parser.add_argument("--method", choices=["engineering", "gpt"], required=True)
    parser.add_argument("--input-dir", default="data/input")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--base-url", default="https://api.openai.com/v1")
    parser.add_argument("--model", default="gpt-4.1-mini")
    parser.add_argument("--timeout", type=int, default=120)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.method == "engineering":
        output_dir = args.output_dir or "data/output/engineering"
        outputs = split_input_folder_engineering(input_dir=args.input_dir, output_dir=output_dir)
    else:
        if not args.api_key:
            raise ValueError("--api-key is required when --method gpt")
        output_dir = args.output_dir or "data/output/gpt"
        outputs = split_input_folder_with_gpt(
            api_key=args.api_key,
            input_dir=args.input_dir,
            output_dir=output_dir,
            base_url=args.base_url,
            model=args.model,
            timeout=args.timeout,
        )

    for path in outputs:
        print(path)


if __name__ == "__main__":
    main()

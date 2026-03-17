from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, cast


TYPE_PATTERN = re.compile(r"\b([PABC])\b", re.IGNORECASE)
TENDER_LABEL_DISPLAY_MAP = {
    "强制-必须偏离": "强制-必须偏离",
    "强制-澄清-Mandatory-Clarification": "强制-澄清",
    "强制-澄清": "强制-澄清",
    "非强制-报价参考-Tutorial-Info": "非强制-报价参考",
    "非强制-报价参考": "非强制-报价参考",
    "非强制-报价行动-Tutorial-Action": "非强制-报价行动",
    "非强制-报价行动": "非强制-报价行动",
}
TENDER_LABEL_ORDER = ["强制-必须偏离", "强制-澄清", "非强制-报价参考", "非强制-报价行动"]


@dataclass(frozen=True)
class KnowledgeEntry:
    entry_id: str
    category: str
    text: str
    type_code: str
    raw_value: str


@dataclass
class KnowledgeBase:
    entries: list[KnowledgeEntry]
    _by_category: dict[str, list[KnowledgeEntry]] = field(default_factory=dict)
    category_order: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self._by_category:
            return
        grouped: dict[str, list[KnowledgeEntry]] = {}
        for entry in self.entries:
            grouped.setdefault(entry.category, []).append(entry)
        self._by_category = grouped

    @property
    def categories(self) -> list[str]:
        return self.category_order or list(self._by_category.keys())

    def by_category(self, category: str) -> list[KnowledgeEntry]:
        return self._by_category.get(category, [])

    def find_entry(self, entry_id: str) -> KnowledgeEntry | None:
        for entry in self.entries:
            if entry.entry_id == entry_id:
                return entry
        return None


def infer_type_code(raw_value: str) -> Literal["P", "A", "B", "C", "OTHER"]:
    if not raw_value:
        return "OTHER"
    match = TYPE_PATTERN.search(raw_value.strip())
    if not match:
        return "OTHER"
    code = match.group(1).upper()
    if code in {"P", "A", "B", "C"}:
        return cast(Literal["P", "A", "B", "C", "OTHER"], code)
    return "OTHER"


def load_knowledge_base(path: Path) -> KnowledgeBase:
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries: list[KnowledgeEntry] = []
    for category, row_list in payload.items():
        if not isinstance(row_list, list):
            continue
        for index, row in enumerate(row_list, start=1):
            if not isinstance(row, dict) or not row:
                continue
            text, raw_value = next(iter(row.items()))
            entry_id = f"{category}-{index}"
            entries.append(
                KnowledgeEntry(
                    entry_id=entry_id,
                    category=str(category),
                    text=str(text),
                    type_code=infer_type_code(str(raw_value)),
                    raw_value=str(raw_value),
                )
            )
    return KnowledgeBase(entries=entries)


def load_tender_instruction_knowledge_base(path: Path) -> KnowledgeBase:
    payload = json.loads(path.read_text(encoding="utf-8"))
    grouped_entries: dict[str, list[KnowledgeEntry]] = {label: [] for label in TENDER_LABEL_ORDER}
    entries: list[KnowledgeEntry] = []

    for source_group, row_list in payload.items():
        if not isinstance(row_list, list):
            continue
        for index, row in enumerate(row_list, start=1):
            if not isinstance(row, dict) or not row:
                continue
            match_text, raw_label = next(iter(row.items()))
            display_label = normalize_tender_label(str(raw_label))
            grouped_entries.setdefault(display_label, [])
            entry = KnowledgeEntry(
                entry_id=f"{source_group}-{index}",
                category=display_label,
                text=str(match_text),
                type_code=display_label,
                raw_value=str(raw_label),
            )
            grouped_entries[display_label].append(entry)
            entries.append(entry)

    return KnowledgeBase(
        entries=entries,
        category_order=[*TENDER_LABEL_ORDER],
        _by_category={label: list(grouped_entries.get(label, [])) for label in TENDER_LABEL_ORDER},
    )


def normalize_tender_label(raw_value: str) -> str:
    normalized = raw_value.strip()
    return TENDER_LABEL_DISPLAY_MAP.get(normalized, normalized or "其他")

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.services.kb_loader import KnowledgeBase, load_knowledge_base, load_tender_instruction_knowledge_base


STANDARD_KB_FILE_NAME = "标准化配套知识库.json"
TENDER_KB_FILE_NAME = "投标说明知识库.json"


@dataclass(frozen=True)
class CompareProfile:
    file_name: str
    display_name: str
    sheet_name: str
    loader: Callable[[Path], KnowledgeBase]


COMPARE_PROFILES: dict[str, CompareProfile] = {
    STANDARD_KB_FILE_NAME: CompareProfile(
        file_name=STANDARD_KB_FILE_NAME,
        display_name="标准化配套知识库",
        sheet_name="标准化配套结果",
        loader=load_knowledge_base,
    ),
    TENDER_KB_FILE_NAME: CompareProfile(
        file_name=TENDER_KB_FILE_NAME,
        display_name="投标说明知识库",
        sheet_name="投标说明结果",
        loader=load_tender_instruction_knowledge_base,
    ),
}


def get_compare_profile(file_name: str) -> CompareProfile:
    try:
        return COMPARE_PROFILES[file_name]
    except KeyError as exc:
        raise ValueError(f"Unsupported compare knowledge base file: {file_name}") from exc

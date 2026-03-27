from __future__ import annotations

import json
from collections.abc import Sequence

from app.services.kb_loader import KnowledgeEntry
from app.services.sentence_splitter import split_sentences


def build_category_messages(
    *,
    chunk_text: str,
    category_keys: list[str],
    category_contexts: Sequence[dict[str, object]] | None = None,
) -> list[dict[str, str]]:
    normalized_contexts = _normalize_category_contexts(category_keys, category_contexts)
    system_prompt = (
        "你是深蓝公司询价响应分析助手。"
        "输入的 chunk 是询价文件中对深蓝公司的要求原文。"
        "输入的 category_keys 是允许返回的分类名称列表。"
        "输入的 category_contexts 是深蓝公司在知识库中已有、能够提供的能力与内容，其中包含分类及样本条目。"
        "请根据语义判断：如果原文要求能够被某个分类下深蓝公司可提供的内容覆盖、满足或响应，则记录该分类。"
        "不要只看字面重合，要判断该分类是否真的能用于响应原文要求。"
        "只返回 JSON 对象：{\"categories\": [string, ...]}。"
        "如果都不匹配则返回空数组。"
        "禁止输出输入中不存在的 category。"
    )
    user_payload = {
        "chunk_background": "chunk 是询价文件中对深蓝公司的要求原文。",
        "chunk": chunk_text,
        "category_keys_background": "category_keys 是允许返回的分类名称列表。",
        "category_keys": category_keys,
        "category_contexts_background": (
            "category_contexts 是深蓝公司知识库中的分类及样本条目，表示深蓝公司能够提供的内容。"
        ),
        "category_contexts": normalized_contexts,
        "rule": "按“深蓝公司可提供内容是否能覆盖、满足或响应原文要求”进行语义判断，可多选。禁止输出输入中不存在的 category。",
    }
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
    ]


def build_item_messages(*, chunk_text: str, category: str, entries: list[KnowledgeEntry]) -> list[dict[str, str]]:
    system_prompt = (
        "你是深蓝公司询价条目匹配助手。"
        "输入的 chunk 是询价文件中对深蓝公司的要求原文。"
        "输入的 category 是已判定可关联的深蓝公司能力分类。"
        "输入的 candidates 是深蓝公司在该分类下能够提供的具体能力、方案或响应内容。"
        "请根据语义判断：哪些候选条目可以用于响应、满足或支撑原文要求。"
        "不要只看字面重合，要判断候选条目是否真的能支持深蓝公司响应该要求。"
        "只返回 JSON 对象：{\"matches\": [{\"entry_id\": string, \"reason\": string}, ...]}。"
        "无匹配返回空数组。"
        "禁止输出输入中不存在的 entry_id。"
    )
    user_payload = {
        "chunk_background": "chunk 是询价文件中对深蓝公司的要求原文。",
        "chunk": chunk_text,
        "category_background": "category 是已判定可关联的深蓝公司能力分类。",
        "category": category,
        "candidates_background": "candidates 是深蓝公司在该分类下能够提供的具体能力、方案或响应内容。",
        "candidates": [
            {
                "entry_id": item.entry_id,
                "text": item.text,
                "type": item.type_code,
            }
            for item in entries
        ],
        "rule": "按“深蓝公司可提供内容是否能响应、满足或支撑原文要求”进行语义判断，可多选。禁止输出输入中不存在的 entry_id。",
    }
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
    ]


def build_batch_category_messages(
    *,
    chunks: list[tuple[int, str]],
    category_keys: list[str],
    category_contexts: Sequence[dict[str, object]] | None = None,
) -> list[dict[str, str]]:
    _validate_unique_chunk_ids(chunks)
    normalized_contexts = _normalize_category_contexts(category_keys, category_contexts)
    system_prompt = (
        "你是深蓝公司询价响应分析助手。"
        "输入的 chunks 是询价文件中对深蓝公司的要求原文。"
        "输入的 category_keys 是允许返回的分类名称列表。"
        "输入的 category_contexts 是深蓝公司在知识库中已有、能够提供的能力与内容，其中包含分类及样本条目。"
        "请逐段判断：如果某段原文要求能够被某个分类下深蓝公司可提供的内容覆盖、满足或响应，则记录该分类。"
        "不要只看字面重合，要判断该分类是否真的能用于响应原文要求。"
        "只返回 JSON：{\"results\":[{\"chunk_id\":int,\"categories\":[string,...]}]}。"
        "如果某段无匹配分类，categories 为空数组。"
        "禁止输出输入中不存在的 chunk_id 或 category。"
    )
    user_payload = {
        "chunks_background": "chunks 是询价文件中对深蓝公司的要求原文。",
        "chunks": [{"chunk_id": chunk_id, "content": text} for chunk_id, text in chunks],
        "category_keys_background": "category_keys 是允许返回的分类名称列表。",
        "category_keys": category_keys,
        "category_contexts_background": (
            "category_contexts 是深蓝公司知识库中的分类及样本条目，表示深蓝公司能够提供的内容。"
        ),
        "category_contexts": normalized_contexts,
        "rule": "按“深蓝公司可提供内容是否能覆盖、满足或响应原文要求”进行语义判断，可多选。禁止输出输入中不存在的 chunk_id 或 category。",
    }
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
    ]


def build_batch_item_messages(
    *,
    category: str,
    entries: list[KnowledgeEntry],
    chunks: Sequence[tuple[int, str] | dict[str, object]],
) -> list[dict[str, str]]:
    _validate_unique_chunk_ids(chunks)
    system_prompt = (
        "你是深蓝公司询价条目匹配助手。"
        "输入的 chunks 是询价文件中对深蓝公司的要求原文。"
        "输入的 category 是已判定可关联的深蓝公司能力分类。"
        "输入的 candidates 是深蓝公司在该分类下能够提供的具体能力、方案或响应内容。"
        "请根据语义判断：哪些候选条目可以用于响应、满足或支撑原文要求。"
        "不要只看字面重合，要判断候选条目是否真的能支持深蓝公司响应该要求。"
        "只返回 JSON：{\"results\":[{\"chunk_id\":int,\"matches\":[{\"entry_id\":string,\"reason\":string,\"evidence_sentence_index\":int,\"evidence_sentence_text\":string}]}]}。"
        "每个命中都必须包含 evidence_sentence_index 和 evidence_sentence_text。"
        "evidence_sentence_index 必须引用该段提供的 sentences.index，evidence_sentence_text 必须与对应 sentences.text 一致。"
        "每段无匹配时 matches 返回空数组。"
        "禁止输出输入中不存在的 chunk_id 或 entry_id。"
    )
    user_payload = {
        "chunks_background": "chunks 是询价文件中对深蓝公司的要求原文。",
        "category": category,
        "category_background": "category 是已判定可关联的深蓝公司能力分类。",
        "candidates_background": "candidates 是深蓝公司在该分类下能够提供的具体能力、方案或响应内容。",
        "candidates": [
            {
                "entry_id": item.entry_id,
                "text": item.text,
                "type": item.type_code,
            }
            for item in entries
        ],
        "chunks": [_build_batch_item_chunk_payload(chunk) for chunk in chunks],
        "rule": "按“深蓝公司可提供内容是否能响应、满足或支撑原文要求”进行语义判断，可多选。禁止输出输入中不存在的 chunk_id 或 entry_id；evidence_sentence_index 必须来自对应的 sentences.index；evidence_sentence_text 必须与对应的 sentences.text 完全一致。",
    }
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
    ]


def _build_batch_item_chunk_payload(chunk: tuple[int, str] | dict[str, object]) -> dict[str, object]:
    if isinstance(chunk, tuple):
        chunk_id, text = chunk
        return {
            "chunk_id": chunk_id,
            "content": text,
            "sentences": _build_sentence_metadata(text),
        }

    payload = {
        "chunk_id": chunk.get("chunk_id"),
        "content": chunk.get("content", ""),
    }
    sentences = chunk.get("sentences")
    if isinstance(sentences, list):
        payload["sentences"] = [
            {
                "index": sentence.get("index"),
                "text": sentence.get("text", ""),
            }
            for sentence in sentences
            if isinstance(sentence, dict)
        ]
    else:
        payload["sentences"] = _build_sentence_metadata(str(payload["content"]))

    return payload


def _normalize_category_contexts(
    category_keys: Sequence[str],
    category_contexts: Sequence[dict[str, object]] | None,
) -> list[dict[str, object]]:
    if category_contexts is None:
        return [{"category": category, "sample_entries": []} for category in category_keys]

    normalized: list[dict[str, object]] = []
    seen_categories: set[str] = set()
    allowed_categories = set(category_keys)
    for context in category_contexts:
        category = context.get("category")
        if not isinstance(category, str):
            continue
        if category not in allowed_categories or category in seen_categories:
            continue
        sample_entries = context.get("sample_entries")
        normalized.append(
            {
                "category": category,
                "sample_entries": _normalize_sample_entries(sample_entries),
            }
        )
        seen_categories.add(category)

    for category in category_keys:
        if category in seen_categories:
            continue
        normalized.append({"category": category, "sample_entries": []})
    return normalized


def _normalize_sample_entries(sample_entries: object) -> list[str]:
    if not isinstance(sample_entries, list):
        return []

    normalized: list[str] = []
    for sample in sample_entries:
        if not isinstance(sample, str):
            continue
        stripped = sample.strip()
        if not stripped:
            continue
        normalized.append(stripped)
    return normalized


def _build_sentence_metadata(text: str) -> list[dict[str, object]]:
    return [
        {"index": index, "text": sentence}
        for index, sentence in enumerate(_split_sentences(text))
    ]


def _split_sentences(text: str) -> list[str]:
    return split_sentences(text)


def _validate_unique_chunk_ids(chunks: Sequence[tuple[int, str] | dict[str, object]]) -> None:
    seen_chunk_ids: set[int] = set()
    for chunk in chunks:
        chunk_id = _get_chunk_id(chunk)
        if chunk_id in seen_chunk_ids:
            raise ValueError("Batch prompt input contains duplicate chunk_id values.")
        seen_chunk_ids.add(chunk_id)


def _get_chunk_id(chunk: tuple[int, str] | dict[str, object]) -> int:
    if isinstance(chunk, tuple):
        chunk_id = chunk[0]
        if isinstance(chunk_id, bool) or not isinstance(chunk_id, int):
            raise ValueError("Batch prompt input chunks must include integer chunk_id values.")
        return chunk_id

    chunk_id = chunk.get("chunk_id")
    if isinstance(chunk_id, bool) or not isinstance(chunk_id, int):
        raise ValueError("Batch prompt input chunks must include integer chunk_id values.")
    return chunk_id

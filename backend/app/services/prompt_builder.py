from __future__ import annotations

import json
from collections.abc import Sequence

from app.services.kb_loader import KnowledgeEntry
from app.services.sentence_splitter import split_sentences


def build_category_messages(*, chunk_text: str, category_keys: list[str]) -> list[dict[str, str]]:
    system_prompt = (
        "你是询价规范分类助手。请判断输入段落属于哪些知识库分类。"
        "只返回 JSON 对象：{\"categories\": [string, ...]}。"
        "如果都不匹配则返回空数组。"
    )
    user_payload = {
        "chunk": chunk_text,
        "category_keys": category_keys,
        "rule": "按语义一致判断，可多选。",
    }
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
    ]


def build_item_messages(*, chunk_text: str, category: str, entries: list[KnowledgeEntry]) -> list[dict[str, str]]:
    system_prompt = (
        "你是询价规范条目匹配助手。"
        "请从候选条目中找出与段落语义一致的条目。"
        "只返回 JSON 对象：{\"matches\": [{\"entry_id\": string, \"reason\": string}, ...]}。"
        "无匹配返回空数组。"
    )
    user_payload = {
        "chunk": chunk_text,
        "category": category,
        "candidates": [
            {
                "entry_id": item.entry_id,
                "text": item.text,
                "type": item.type_code,
            }
            for item in entries
        ],
        "rule": "按语义一致判断，可多选。",
    }
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
    ]


def build_batch_category_messages(
    *,
    chunks: list[tuple[int, str]],
    category_keys: list[str],
) -> list[dict[str, str]]:
    _validate_unique_chunk_ids(chunks)
    system_prompt = (
        "你是询价规范分类助手。"
        "现在会输入多个段落，请逐段判断所属分类。"
        "只返回 JSON：{\"results\":[{\"chunk_id\":int,\"categories\":[string,...]}]}。"
        "如果某段无匹配分类，categories 为空数组。"
    )
    user_payload = {
        "chunks": [{"chunk_id": chunk_id, "content": text} for chunk_id, text in chunks],
        "category_keys": category_keys,
        "rule": "按语义一致判断，可多选。禁止输出输入中不存在的 chunk_id。",
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
        "你是询价规范条目匹配助手。"
        "给定一个分类及其条目，再给定多个段落，请逐段返回命中条目。"
        "只返回 JSON：{\"results\":[{\"chunk_id\":int,\"matches\":[{\"entry_id\":string,\"reason\":string,\"evidence_sentence_index\":int,\"evidence_sentence_text\":string}]}]}。"
        "每个命中都必须包含 evidence_sentence_index 和 evidence_sentence_text。"
        "evidence_sentence_index 必须引用该段提供的 sentences.index，evidence_sentence_text 必须与对应 sentences.text 一致。"
        "每段无匹配时 matches 返回空数组。"
    )
    user_payload = {
        "category": category,
        "candidates": [
            {
                "entry_id": item.entry_id,
                "text": item.text,
                "type": item.type_code,
            }
            for item in entries
        ],
        "chunks": [_build_batch_item_chunk_payload(chunk) for chunk in chunks],
        "rule": "按语义一致判断，可多选。禁止输出输入中不存在的 chunk_id 或 entry_id；evidence_sentence_index 必须来自对应的 sentences.index；evidence_sentence_text 必须与对应的 sentences.text 完全一致。",
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

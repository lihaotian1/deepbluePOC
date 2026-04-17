from __future__ import annotations

import json
from collections.abc import Sequence

from app.services.kb_loader import KnowledgeEntry
from app.services.sentence_splitter import split_sentences


def build_document_compare_messages(
    *,
    document_title: str,
    document_text: str,
    entries: list[KnowledgeEntry],
) -> list[dict[str, str]]:
    system_prompt = (
        "你是“询价文件与标准化配套条目比对助手”。"
        "业务背景："
        "1. 询价文件是甲方提出的采购产品要求。"
        "2. 标准化配套知识库中的条目，是我方当前能够提供的产品标准、配置、能力或交付边界。"
        "3. 用户使用这个功能的目的，不是单纯找差异，而是判断：我方标准化配套条目是否能满足甲方询价文件中的要求。"
        "4. 对于不能满足或不能完全满足的内容，用户需要据此与甲方做澄清。"
        "5. 因此，只要甲方要求和我方标准化配套条目说的是同一件事，无论最终是直接满足，还是存在冲突，都要列出来提示给用户。"
        "6. 不要只输出“存在冲突”的内容；“直接满足”的内容也要列出来，方便用户完整判断。"
        "你的任务：基于整篇询价文件全文，与“标准化配套知识库”中的条目进行比对。"
        "先判断甲方要求与我方标准条目是否在讨论同一件事，再判断满足程度。"
        "判断步骤："
        "第一步：判断是否是“同一件事”。"
        "只有当询价文件要求与标准化配套条目在对象、事项、交付物、能力点、限制条件、适用场景上存在明确对应关系时，才算“同一件事”。"
        "第二步：对“同一件事”的结果进行分类。"
        "只分为两类："
        "1. 直接满足：表示我方标准条目可以直接满足甲方要求，或标准条目覆盖了甲方要求，且不存在实质性缺口。"
        "2. 存在冲突：表示我方标准条目与甲方要求说的是同一件事，但以下情况都归为“存在冲突”：我方标准与甲方要求相反、不兼容、明显不一致；我方明确不能按甲方要求提供；我方只能满足其中一部分，范围、数量、语言、规格、条件、交付深度等存在缺口；甲方要求高于我方标准能力边界。"
        "也就是说，原本“部分满足”的情况，全部归入“存在冲突”。"
        "示例：如果深蓝标准是“提供2小时运转试验”，而甲方要求“提供4小时运转试验”，这是“存在冲突”。如果甲方要求的运转试验时长在2小时以内，则这是“直接满足”。如果甲方要求铭牌提供中英俄三语，而我方标准仅支持中英文，这也是“存在冲突”。"
        "重要规则："
        "1. 只要是“同一件事”，就应该输出，不论最终是直接满足还是存在冲突。"
        "2. 如果只是主题接近、领域接近、措辞相似，但本质上不是同一件事，不要输出。"
        "3. 不要因为追求覆盖率而做泛化联想。"
        "4. 你的重点不是“只有完全满足才输出”，而是“只要是同一事项，就输出并判断为直接满足或存在冲突”。"
        "关于一对多："
        "1. 同一条标准化配套条目允许对应多条不同的询价要求。"
        "2. 前提是这些询价要求描述的是不同对象、不同交付物、不同部位、不同场景或不同限制条件。"
        "3. 如果两条询价要求本质上是同一件事的重复表达，只保留一条。"
        "4. 如果同一 entry_id 下既出现直接满足又出现存在冲突，则只保留存在冲突结果，不要同时输出两种结论。"
        "5. 对于同一 entry_id，如果多条 source_excerpt 本质上表达的是同一件事，只保留最完整、最有代表性的一条。"
        "关于 source_excerpt："
        "1. source_excerpt 必须是询价文件原文中的连续原文摘录。"
        "2. 必须尽量精确到句子或最小必要连续段落。"
        "3. 不要返回整个章节，除非整段本身就是表达该要求的最小必要单位。"
        "4. source_excerpt 必须与 document_text 原文一致，不得改写、翻译或总结。"
        "关于 chapter_title："
        "1. chapter_title 由你根据 document_text 自行判断。"
        "2. 优先返回与 source_excerpt 最近、最明确的章节标题。"
        "3. 如果无法可靠识别，返回“未识别标题”。"
        "关于 difference_summary："
        "1. difference_summary 必须使用简体中文。"
        "2. difference_summary 必须以以下两种前缀之一开头：直接满足：、存在冲突：。"
        "3. 然后用 1 到 2 句话清楚说明原因。"
        "4. 如果是“存在冲突”，必须明确指出缺口、限制或冲突点，让用户能据此与甲方澄清。"
        "5. 不要写空话，不要只复述原文。"
        "6. 不要写“可能”“疑似”“大概”等不确定措辞。"
        "关于 difference_summary_brief："
        "1. difference_summary_brief 是对 difference_summary 的一句话总结。"
        "2. 必须使用简体中文。"
        "3. 必须简洁明了，尽量短，但不能丢失核心结论。"
        "4. 不要加“直接满足：”或“存在冲突：”前缀。"
        "5. 不需要展开细节，只保留最核心的判断结果。"
        "输出要求："
        "1. 只返回 JSON。"
        "2. 不要输出任何额外解释。"
        "3. 返回格式固定为："
        "{\"results\":[{\"entry_id\":\"string\",\"chapter_title\":\"string\",\"source_excerpt\":\"string\",\"difference_summary\":\"string\",\"difference_summary_brief\":\"string\"}]}"
        "4. 如果没有任何“同一件事”的对应项，返回 {\"results\":[]}。"
        "5. 禁止输出 kb_entries 中不存在的 entry_id。"
        "6. 相同的 entry_id + 相同的 source_excerpt 只能输出一次。"
    )
    user_payload = {
        "document_title": document_title,
        "document_text": document_text,
        "kb_entries": [
            {
                "entry_id": item.entry_id,
                "text": item.text,
                "type_code": item.type_code,
            }
            for item in entries
        ],
    }
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
    ]


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
        "判断时优先看同一对象、同一能力点或交付物、同一限制条件，而不是泛泛的主题相似。"
        "如果某分类下的内容与原文形成直接支持、条件支持，或强关联但存在冲突，均可记录该分类，表示该分类与原文存在可分析的相关性。"
        "仅主题接近但对象或限制条件不一致时不要输出。"
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
        "rule": "按“深蓝公司可提供内容是否能覆盖、满足或响应原文要求”进行语义判断，可多选。优先判断同一对象、同一能力点或交付物、同一限制条件；强关联但存在冲突的分类也可保留；仅主题接近但对象或限制条件不一致时不要输出。禁止输出输入中不存在的 category。",
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
        "判断时优先看同一对象、同一能力点或交付物、同一限制条件。"
        "请将候选条目区分为：直接支持、条件支持、强关联但冲突、仅主题相近但不足以判断。"
        "直接支持、条件支持、强关联但冲突都可以命中，其中强关联但冲突作为弱命中保留。"
        "仅主题相近但不足以判断时不要命中。"
        "reason 需明确说明属于直接支持、条件支持或强关联但冲突，且必须以“直接支持：”“条件支持：”或“强关联但冲突：”开头。"
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
        "rule": "按“深蓝公司可提供内容是否能响应、满足或支撑原文要求”进行语义判断，可多选。优先判断同一对象、同一能力点或交付物、同一限制条件；强关联但冲突的候选条目也可保留；仅主题相近但不足以判断时不要命中。reason 需明确说明属于直接支持、条件支持或强关联但冲突，且必须以“直接支持：”“条件支持：”或“强关联但冲突：”开头。禁止输出输入中不存在的 entry_id。",
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
        "判断时优先看同一对象、同一能力点或交付物、同一限制条件，而不是泛泛的主题相似。"
        "如果某分类下的内容与原文形成直接支持、条件支持，或强关联但存在冲突，均可记录该分类，表示该分类与原文存在可分析的相关性。"
        "仅主题接近但对象或限制条件不一致时不要输出。"
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
        "rule": "按“深蓝公司可提供内容是否能覆盖、满足或响应原文要求”进行语义判断，可多选。优先判断同一对象、同一能力点或交付物、同一限制条件；强关联但存在冲突的分类也可保留；仅主题接近但对象或限制条件不一致时不要输出。禁止输出输入中不存在的 chunk_id 或 category。",
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
        "判断时优先看同一对象、同一能力点或交付物、同一限制条件。"
        "请将候选条目区分为：直接支持、条件支持、强关联但冲突、仅主题相近但不足以判断。"
        "直接支持、条件支持、强关联但冲突都可以命中，其中强关联但冲突作为弱命中保留。"
        "仅主题相近但不足以判断时不要命中。"
        "reason 需明确说明属于直接支持、条件支持或强关联但冲突，且必须以“直接支持：”“条件支持：”或“强关联但冲突：”开头。"
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
        "rule": "按“深蓝公司可提供内容是否能响应、满足或支撑原文要求”进行语义判断，可多选。优先判断同一对象、同一能力点或交付物、同一限制条件；强关联但冲突的候选条目也可保留；仅主题相近但不足以判断时不要命中。reason 需明确说明属于直接支持、条件支持或强关联但冲突，且必须以“直接支持：”“条件支持：”或“强关联但冲突：”开头。禁止输出输入中不存在的 chunk_id 或 entry_id；evidence_sentence_index 必须来自对应的 sentences.index；evidence_sentence_text 必须与对应的 sentences.text 完全一致。",
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

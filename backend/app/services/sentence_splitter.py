from __future__ import annotations

import re

SENTENCE_TERMINATORS = {"。", "！", "？", ".", "!", "?", ";", "；", "\n", "\r"}
INITIALISM_SENTENCE_STARTER_WORDS = {
    "next",
    "this",
    "that",
    "these",
    "those",
    "another",
    "first",
    "second",
    "third",
    "final",
    "however",
    "meanwhile",
    "therefore",
    "today",
    "tomorrow",
    "yesterday",
}


def split_sentences(text: str) -> list[str]:
    sentences: list[str] = []
    start = 0

    for index, _ in enumerate(text):
        if not _is_sentence_terminator(text, index):
            continue

        sentence = text[start : index + 1].strip()
        if sentence:
            sentences.append(sentence)
            start = index + 1

    tail = text[start:].strip()
    if tail:
        sentences.append(tail)

    return sentences


def _is_sentence_terminator(text: str, index: int) -> bool:
    character = text[index]
    if character not in SENTENCE_TERMINATORS:
        return False

    if character != ".":
        return True

    if _is_protected_abbreviation_dot(text, index):
        return False

    if _is_number_label_dot(text, index):
        return False

    if _is_technical_token_dot(text, index):
        return False

    if _is_initialism_continuation_dot(text, index):
        return False

    return not (_is_digit(_char_at(text, index - 1)) and _is_digit(_char_at(text, index + 1)))


def _is_protected_abbreviation_dot(text: str, index: int) -> bool:
    return _is_dot_within_literal(text, index, "e.g.") or _is_dot_within_literal(text, index, "i.e.")


def _is_dot_within_literal(text: str, index: int, literal: str) -> bool:
    normalized_text = text.lower()
    start_min = max(0, index - len(literal) + 1)
    start_max = min(index, len(normalized_text) - len(literal))
    for start in range(start_min, start_max + 1):
        if normalized_text[start : start + len(literal)] == literal:
            return True
    return False


def _is_number_label_dot(text: str, index: int) -> bool:
    left_slice = text[max(0, index - 2) : index]
    right_slice = text[index + 1 :]
    return bool(re.search(r"\bno$", left_slice, flags=re.IGNORECASE)) and bool(
        re.match(r"\s*\d", right_slice)
    )


def _is_technical_token_dot(text: str, index: int) -> bool:
    return _is_technical_token_character(_char_at(text, index - 1)) and _is_technical_token_character(
        _char_at(text, index + 1)
    )


def _is_technical_token_character(character: str | None) -> bool:
    return character is not None and bool(re.match(r"[A-Za-z0-9_-]", character))


def _is_initialism_continuation_dot(text: str, index: int) -> bool:
    initialism_match = re.search(r"(?:^|[^A-Za-z])((?:[A-Za-z]\.){2,})$", text[: index + 1])
    if initialism_match is None:
        return False

    segment_count = len(re.findall(r"[A-Za-z]\.", initialism_match.group(1)))
    next_text = text[index + 1 :]

    if re.match(r"\s*[a-z0-9]", next_text):
        return True

    if segment_count != 2:
        return False

    uppercase_word_match = re.match(r"\s*([A-Z][a-z]+)", next_text)
    uppercase_word = uppercase_word_match.group(1).lower() if uppercase_word_match else None
    return uppercase_word is not None and uppercase_word not in INITIALISM_SENTENCE_STARTER_WORDS


def _char_at(text: str, index: int) -> str | None:
    if index < 0 or index >= len(text):
        return None
    return text[index]


def _is_digit(character: str | None) -> bool:
    return character is not None and "0" <= character <= "9"

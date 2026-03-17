import type { ChunkCompareResult, MatchItem, TypeCode } from "../types";

export interface ReasonHighlightState {
  reasonKey: string;
  sentenceIndex: number;
}

export interface SourceSentenceSegment {
  index: number;
  text: string;
  comparableText: string;
}

export interface SourceSentenceViewModel {
  index: number;
  text: string;
  isActive: boolean;
}

export interface ChunkCompareDisplayState {
  state: "pending" | "no-hit" | "hit";
  resultTypeCodes: TypeCode[];
}

export interface ReasonHighlightPresentationState {
  isClickable: boolean;
  isActive: boolean;
}

const SENTENCE_TERMINATORS = new Set(["。", "！", "？", ".", "!", "?", ";", "；", "\n", "\r"]);
const INITIALISM_SENTENCE_STARTER_WORDS = new Set([
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
]);

type ReasonHighlightMatch = Pick<
  MatchItem,
  "entry_id" | "reason" | "evidence_sentence_index" | "evidence_sentence_text"
>;

export function splitChunkContentIntoSentences(text: string): SourceSentenceSegment[] {
  const sentences: SourceSentenceSegment[] = [];
  let sentenceIndex = 0;
  let start = 0;

  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    if (!isSentenceTerminator(text, index)) {
      continue;
    }

    const sentenceText = text.slice(start, index + 1);
    const comparableText = sentenceText.trim();
    if (comparableText) {
      sentences.push({ index: sentenceIndex, text: sentenceText, comparableText });
      sentenceIndex += 1;
      start = index + 1;
    }
  }

  const sentenceText = text.slice(start);
  const comparableText = sentenceText.trim();
  if (comparableText) {
    sentences.push({ index: sentenceIndex, text: sentenceText, comparableText });
  }

  return sentences;
}

function isSentenceTerminator(text: string, index: number): boolean {
  const character = text[index];
  if (!SENTENCE_TERMINATORS.has(character)) {
    return false;
  }

  if (character !== ".") {
    return true;
  }

  if (isProtectedAbbreviationDot(text, index)) {
    return false;
  }

  if (isNumberLabelDot(text, index)) {
    return false;
  }

  if (isTechnicalTokenDot(text, index)) {
    return false;
  }

  if (isInitialismContinuationDot(text, index)) {
    return false;
  }

  return !isDigit(text[index - 1]) || !isDigit(text[index + 1]);
}

function isProtectedAbbreviationDot(text: string, index: number): boolean {
  return isDotWithinLiteral(text, index, "e.g.") || isDotWithinLiteral(text, index, "i.e.");
}

function isDotWithinLiteral(text: string, index: number, literal: string): boolean {
  const normalizedText = text.toLowerCase();
  const startMin = Math.max(0, index - literal.length + 1);
  const startMax = Math.min(index, normalizedText.length - literal.length);

  for (let start = startMin; start <= startMax; start += 1) {
    if (normalizedText.slice(start, start + literal.length) !== literal) {
      continue;
    }

    return true;
  }

  return false;
}

function isNumberLabelDot(text: string, index: number): boolean {
  return /\bno$/i.test(text.slice(Math.max(0, index - 2), index)) && /^\s*\d/.test(text.slice(index + 1));
}

function isTechnicalTokenDot(text: string, index: number): boolean {
  return isTechnicalTokenCharacter(text[index - 1]) && isTechnicalTokenCharacter(text[index + 1]);
}

function isTechnicalTokenCharacter(character: string | undefined): boolean {
  return character !== undefined && /[A-Za-z0-9_-]/.test(character);
}

function isInitialismContinuationDot(text: string, index: number): boolean {
  const initialismMatch = text.slice(0, index + 1).match(/(?:^|[^A-Za-z])((?:[A-Za-z]\.){2,})$/);
  if (!initialismMatch) {
    return false;
  }

  const segmentCount = (initialismMatch[1].match(/[A-Za-z]\./g) ?? []).length;
  const nextText = text.slice(index + 1);

  if (/^\s*[a-z0-9]/.test(nextText)) {
    return true;
  }

  if (segmentCount !== 2) {
    return false;
  }

  const uppercaseWord = nextText.match(/^\s*([A-Z][a-z]+)/)?.[1]?.toLowerCase();
  return uppercaseWord !== undefined && !INITIALISM_SENTENCE_STARTER_WORDS.has(uppercaseWord);
}

function isDigit(character: string | undefined): boolean {
  return character !== undefined && character >= "0" && character <= "9";
}

export function buildSourceSentenceViewModels(
  sentences: readonly SourceSentenceSegment[],
  activeHighlight: ReasonHighlightState | null,
): SourceSentenceViewModel[] {
  return sentences.map((sentence) => ({
    index: sentence.index,
    text: sentence.text,
    isActive: activeHighlight?.sentenceIndex === sentence.index,
  }));
}

export function getReasonHighlightKey(match: Pick<ReasonHighlightMatch, "entry_id" | "reason">): string {
  return `${match.entry_id}::${match.reason}`;
}

export function getReasonHighlightResetKey(chunkContent: string, result?: ChunkCompareResult): string {
  if (!result) {
    return `${chunkContent}::pending`;
  }

  return JSON.stringify({
    chunkContent,
    label: result.label,
    matches: result.matches.map((match) => ({
      entry_id: match.entry_id,
      reason: match.reason,
      evidence_sentence_index: match.evidence_sentence_index ?? null,
      evidence_sentence_text: match.evidence_sentence_text ?? "",
    })),
  });
}

export function normalizeChunkCompareResultDisplay(result?: ChunkCompareResult): ChunkCompareDisplayState {
  if (!result) {
    return {
      state: "pending",
      resultTypeCodes: [],
    };
  }

  if (result.label === "其他" || result.matches.length === 0) {
    return {
      state: "no-hit",
      resultTypeCodes: ["OTHER"],
    };
  }

  return {
    state: "hit",
    resultTypeCodes: Array.from(new Set(result.matches.map((item) => item.type_code))),
  };
}

export function isReasonHighlightable(match: ReasonHighlightMatch, sentences: readonly SourceSentenceSegment[]): boolean {
  return resolveReasonSentenceIndex(match, sentences) !== null;
}

export function getReasonHighlightPresentationState(
  activeHighlight: ReasonHighlightState | null,
  match: ReasonHighlightMatch,
  sentences: readonly SourceSentenceSegment[],
): ReasonHighlightPresentationState {
  const sentenceIndex = resolveReasonSentenceIndex(match, sentences);
  if (sentenceIndex === null) {
    return {
      isClickable: false,
      isActive: false,
    };
  }

  return {
    isClickable: true,
    isActive: activeHighlight?.reasonKey === getReasonHighlightKey(match) && activeHighlight.sentenceIndex === sentenceIndex,
  };
}

export function toggleReasonHighlight(
  currentHighlight: ReasonHighlightState | null,
  match: ReasonHighlightMatch,
  sentences: readonly SourceSentenceSegment[],
): ReasonHighlightState | null {
  const sentenceIndex = resolveReasonSentenceIndex(match, sentences);
  if (sentenceIndex === null) {
    return currentHighlight;
  }

  const reasonKey = getReasonHighlightKey(match);
  if (currentHighlight?.reasonKey === reasonKey) {
    return null;
  }

  return { reasonKey, sentenceIndex };
}

function resolveReasonSentenceIndex(match: ReasonHighlightMatch, sentences: readonly SourceSentenceSegment[]): number | null {
  const rawIndex = match.evidence_sentence_index;
  if (typeof rawIndex === "number" && Number.isInteger(rawIndex) && rawIndex >= 0 && rawIndex < sentences.length) {
    return rawIndex;
  }

  const evidenceText = match.evidence_sentence_text?.trim();
  if (!evidenceText) {
    return null;
  }

  const matchingSentences = sentences.filter((sentence) => sentence.comparableText === evidenceText);
  return matchingSentences.length === 1 ? matchingSentences[0].index : null;
}

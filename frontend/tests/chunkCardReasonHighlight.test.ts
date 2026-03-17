import assert from "node:assert/strict";
import test from "node:test";

import {
  buildSourceSentenceViewModels,
  getReasonHighlightPresentationState,
  getReasonHighlightResetKey,
  isReasonHighlightable,
  normalizeChunkCompareResultDisplay,
  splitChunkContentIntoSentences,
  toggleReasonHighlight,
} from "../src/components/chunkCardReasonHighlight.ts";

const chunk = {
  chunk_id: 1,
  source: "demo.pdf",
  heading: "6.1 SUPPLY INCLUSIONS",
  level: 2,
  line_no: 1,
  content:
    "Pump shall include bearings. Optional vibration detectors wired to an auxiliary conduit box. The baseplate shall be painted.",
};

const clickableMatch = {
  entry_id: "Bearings-1",
  category: "轴承/轴承箱体Bearings / Bearing Housing",
  text: "可选的振动探测器远传至接线箱结构Optional vibration detectors wired to an auxiliary conduit box",
  type_code: "B" as const,
  reason: "原文第二句明确写到可选的振动探测器远传至接线箱结构",
  evidence_sentence_index: 1,
  evidence_sentence_text: "Optional vibration detectors wired to an auxiliary conduit box.",
};

test("clicking a rendered reason highlights exactly one source sentence", () => {
  const sentences = splitChunkContentIntoSentences(chunk.content);

  const activeHighlight = toggleReasonHighlight(null, clickableMatch, sentences);
  const viewModels = buildSourceSentenceViewModels(sentences, activeHighlight);

  assert.equal(activeHighlight?.sentenceIndex, 1);
  assert.deepEqual(getReasonHighlightPresentationState(activeHighlight, clickableMatch, sentences), {
    isActive: true,
    isClickable: true,
  });
  assert.equal(viewModels.filter((item) => item.isActive).length, 1);
  assert.deepEqual(
    viewModels.map((item) => ({ text: item.text, isActive: item.isActive })),
    [
      { text: "Pump shall include bearings.", isActive: false },
      {
        text: " Optional vibration detectors wired to an auxiliary conduit box.",
        isActive: true,
      },
      { text: " The baseplate shall be painted.", isActive: false },
    ],
  );
});

test("clicking the same reason again clears the highlight", () => {
  const sentences = splitChunkContentIntoSentences(chunk.content);
  const activeHighlight = toggleReasonHighlight(null, clickableMatch, sentences);

  assert.deepEqual(toggleReasonHighlight(activeHighlight, clickableMatch, sentences), null);
});

test("a reason without usable evidence metadata does not activate highlighting", () => {
  const unusableMatch = {
    ...clickableMatch,
    entry_id: "Bearings-2",
    reason: "只有摘要，没有可追踪句子",
    evidence_sentence_index: null,
    evidence_sentence_text: "This text does not match any source sentence.",
  };
  const sentences = splitChunkContentIntoSentences(chunk.content);
  const activeHighlight = toggleReasonHighlight(null, unusableMatch, sentences);
  const viewModels = buildSourceSentenceViewModels(sentences, activeHighlight);

  assert.equal(isReasonHighlightable(unusableMatch, sentences), false);
  assert.deepEqual(getReasonHighlightPresentationState(activeHighlight, unusableMatch, sentences), {
    isActive: false,
    isClickable: false,
  });
  assert.equal(activeHighlight, null);
  assert.equal(viewModels.filter((item) => item.isActive).length, 0);
});

test("text fallback highlights when there is a unique exact sentence match", () => {
  const fallbackMatch = {
    ...clickableMatch,
    entry_id: "Bearings-3",
    reason: "证据文本唯一匹配第二句",
    evidence_sentence_index: null,
  };
  const sentences = splitChunkContentIntoSentences(chunk.content);

  assert.equal(isReasonHighlightable(fallbackMatch, sentences), true);
  const activeHighlight = toggleReasonHighlight(null, fallbackMatch, sentences);

  assert.equal(activeHighlight?.sentenceIndex, 1);
  assert.deepEqual(getReasonHighlightPresentationState(activeHighlight, fallbackMatch, sentences), {
    isActive: true,
    isClickable: true,
  });
});

test("duplicate sentence text fallback stays inactive when the exact match is ambiguous", () => {
  const duplicateChunk = "Repeat sentence. Repeat sentence. Final sentence.";
  const ambiguousMatch = {
    ...clickableMatch,
    entry_id: "Bearings-4",
    reason: "重复句子无法唯一定位",
    evidence_sentence_index: null,
    evidence_sentence_text: "Repeat sentence.",
  };
  const sentences = splitChunkContentIntoSentences(duplicateChunk);

  assert.equal(isReasonHighlightable(ambiguousMatch, sentences), false);
  assert.equal(toggleReasonHighlight(null, ambiguousMatch, sentences), null);
});

test("sentence split view models preserve original whitespace and newline formatting", () => {
  const formattedChunk = "First sentence.\n  Second sentence with indent.\n\nThird sentence.";
  const sentences = splitChunkContentIntoSentences(formattedChunk);
  const viewModels = buildSourceSentenceViewModels(sentences, null);

  assert.equal(viewModels.map((item) => item.text).join(""), formattedChunk);
  assert.deepEqual(
    viewModels.map((item) => item.text),
    ["First sentence.", "\n  Second sentence with indent.", "\n\nThird sentence."],
  );
});

test("decimal and version-number content does not split on internal dots", () => {
  const decimalChunk = "API 610 section 8.2 requires 3.5 mm clearance. Firmware v2.1.3 remains supported.";
  const sentences = splitChunkContentIntoSentences(decimalChunk);

  assert.deepEqual(
    sentences.map((item) => item.comparableText),
    ["API 610 section 8.2 requires 3.5 mm clearance.", "Firmware v2.1.3 remains supported."],
  );
  assert.equal(sentences.map((item) => item.text).join(""), decimalChunk);
});

test("valid evidence index stays authoritative even when local text fallback would disagree", () => {
  const decimalChunk = "API 610 section 8.2 requires 3.5 mm clearance. Firmware v2.1.3 remains supported.";
  const sentences = splitChunkContentIntoSentences(decimalChunk);
  const mismatchMatch = {
    ...clickableMatch,
    entry_id: "Bearings-5",
    reason: "索引优先于本地文本回退",
    evidence_sentence_index: 1,
    evidence_sentence_text: "API 610 section 8.2 requires 3.5 mm clearance.",
  };

  const activeHighlight = toggleReasonHighlight(null, mismatchMatch, sentences);

  assert.equal(activeHighlight?.sentenceIndex, 1);
  assert.deepEqual(getReasonHighlightPresentationState(activeHighlight, mismatchMatch, sentences), {
    isActive: true,
    isClickable: true,
  });
});

test("abbreviation-style dots do not split obvious e.g., i.e., and No. cases", () => {
  const abbreviationChunk =
    "Use e.g. inspection logs for reference. Clarify i.e. the sealing plan before review. No. 5 pump remains optional.";
  const sentences = splitChunkContentIntoSentences(abbreviationChunk);

  assert.deepEqual(
    sentences.map((item) => item.comparableText),
    [
      "Use e.g. inspection logs for reference.",
      "Clarify i.e. the sealing plan before review.",
      "No. 5 pump remains optional.",
    ],
  );
});

test("dot-heavy technical text keeps domains emails files and initialisms intact", () => {
  const technicalChunk =
    "Visit portal.example.com for updates. Email qa.team@example.com before noon. Attach report.v2.1.pdf to the ticket. U.S.A. vendor data remains acceptable.";
  const sentences = splitChunkContentIntoSentences(technicalChunk);

  assert.deepEqual(
    sentences.map((item) => item.comparableText),
    [
      "Visit portal.example.com for updates.",
      "Email qa.team@example.com before noon.",
      "Attach report.v2.1.pdf to the ticket.",
      "U.S.A. vendor data remains acceptable.",
    ],
  );
});

test("dotted initialisms still split at sentence boundaries", () => {
  const initialismBoundaryChunk = "U.S.A. Next sentence starts here.";
  const sentences = splitChunkContentIntoSentences(initialismBoundaryChunk);

  assert.deepEqual(sentences.map((item) => item.comparableText), ["U.S.A.", "Next sentence starts here."]);
});

test("two-letter dotted initialisms can continue into uppercase technical phrases", () => {
  const uppercaseContinuationChunk = "U.S. Government guidance remains applicable. U.K. Export controls still apply.";
  const sentences = splitChunkContentIntoSentences(uppercaseContinuationChunk);

  assert.deepEqual(sentences.map((item) => item.comparableText), [
    "U.S. Government guidance remains applicable.",
    "U.K. Export controls still apply.",
  ]);
});

test("two-letter dotted initialisms stay attached to broader institutional phrases", () => {
  const institutionalChunk =
    "U.S. Senate guidance remains applicable. U.N. Security Council review continues. E.U. Parliament vote is pending.";
  const sentences = splitChunkContentIntoSentences(institutionalChunk);

  assert.deepEqual(sentences.map((item) => item.comparableText), [
    "U.S. Senate guidance remains applicable.",
    "U.N. Security Council review continues.",
    "E.U. Parliament vote is pending.",
  ]);
});

test("two-letter dotted initialisms still split before generic uppercase sentence starters", () => {
  const boundaryChunk = "U.S. Next sentence starts here.";
  const sentences = splitChunkContentIntoSentences(boundaryChunk);

  assert.deepEqual(sentences.map((item) => item.comparableText), ["U.S.", "Next sentence starts here."]);
});

test("reason highlight reset key ignores harmless result identity churn but changes for evidence payload updates", () => {
  const baseResult = {
    chunk_id: 1,
    heading: "6.1 SUPPLY INCLUSIONS",
    content: chunk.content,
    categories: ["轴承/轴承箱体Bearings / Bearing Housing"],
    matches: [clickableMatch],
    label: "命中" as const,
  };
  const samePayloadResult = {
    ...baseResult,
    categories: [...baseResult.categories],
    matches: [{ ...clickableMatch }],
  };
  const changedEvidenceResult = {
    ...baseResult,
    matches: [
      {
        ...clickableMatch,
        evidence_sentence_index: 2,
      },
    ],
  };

  assert.equal(
    getReasonHighlightResetKey(chunk.content, baseResult),
    getReasonHighlightResetKey(chunk.content, samePayloadResult),
  );
  assert.notEqual(
    getReasonHighlightResetKey(chunk.content, baseResult),
    getReasonHighlightResetKey(chunk.content, changedEvidenceResult),
  );
});

test('display normalization treats label "命中" with empty matches as a no-hit state', () => {
  const normalized = normalizeChunkCompareResultDisplay({
    chunk_id: 1,
    heading: chunk.heading,
    content: chunk.content,
    categories: ["轴承/轴承箱体Bearings / Bearing Housing"],
    matches: [],
    label: "命中",
  });

  assert.deepEqual(normalized, {
    state: "no-hit",
    resultTypeCodes: ["OTHER"],
  });
});

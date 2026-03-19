import assert from "node:assert/strict";
import test from "node:test";

import {
  addManualReviewMatch,
  buildManualReviewMatch,
  markChunkReviewed,
  normalizeReviewResult,
  removeReviewMatch,
  setOtherReviewOpinion,
  updateReviewMatchReason,
} from "../src/pages/homePageReviewState.ts";
import type { ChunkCompareResult } from "../src/types";

function buildResult(): ChunkCompareResult {
  return {
    chunk_id: 1,
    heading: "1.1",
    content: "source",
    categories: ["分类A"],
    matches: [
      {
        entry_id: "kb-1",
        category: "分类A",
        text: "符合 API 610",
        type_code: "P",
        reason: "模型意见",
        evidence_sentence_index: 0,
        evidence_sentence_text: "source",
      },
    ],
    label: "命中",
    review_status: "未审",
  };
}

test("normalizeReviewResult defaults missing review state to 未审", () => {
  const normalized = normalizeReviewResult({
    ...buildResult(),
    review_status: undefined as unknown as "已审" | "未审",
  });

  assert.equal(normalized.review_status, "未审");
});

test("markChunkReviewed flips the review status to 已审", () => {
  const reviewed = markChunkReviewed(buildResult());

  assert.equal(reviewed.review_status, "已审");
});

test("updating a match reason resets the chunk to 未审", () => {
  const updated = updateReviewMatchReason(
    markChunkReviewed(buildResult()),
    "kb-1",
    "人工意见",
  );

  assert.equal(updated.review_status, "未审");
  assert.equal(updated.matches[0]?.reason, "人工意见");
});

test("removing the last match turns the chunk into 其他 and resets review state", () => {
  const updated = removeReviewMatch(markChunkReviewed(buildResult()), "kb-1");

  assert.equal(updated.label, "其他");
  assert.deepEqual(updated.matches, []);
  assert.deepEqual(updated.categories, []);
  assert.equal(updated.review_status, "未审");
});

test("buildManualReviewMatch uses the default opinion for 其他", () => {
  const match = buildManualReviewMatch({
    entryId: "manual-other",
    category: "其他",
    text: "",
    typeCode: "OTHER",
    reason: "",
  });

  assert.equal(match.reason, "未命中知识库条目，归类为其他。");
  assert.equal(match.evidence_sentence_index, null);
  assert.equal(match.evidence_sentence_text, "");
});

test("adding a manual match appends the row and resets review state", () => {
  const updated = addManualReviewMatch(
    markChunkReviewed(buildResult()),
    buildManualReviewMatch({
      entryId: "manual-1",
      category: "分类B",
      text: "人工补充条目",
      typeCode: "B",
      reason: "人工审核意见",
    }),
  );

  assert.equal(updated.review_status, "未审");
  assert.equal(updated.label, "命中");
  assert.equal(updated.matches.length, 2);
  assert.deepEqual(updated.categories, ["分类A", "分类B"]);
});

test("adding only an 其他 row keeps the chunk in 其他 state", () => {
  const updated = addManualReviewMatch(
    {
      ...buildResult(),
      matches: [],
      categories: [],
      label: "其他",
    },
    buildManualReviewMatch({
      entryId: "manual-other",
      category: "其他",
      text: "未命中知识库条目，归类为其他。",
      typeCode: "OTHER",
      reason: "补充其他意见",
    }),
  );

  assert.equal(updated.label, "其他");
  assert.deepEqual(updated.categories, []);
  assert.equal(updated.matches[0]?.reason, "补充其他意见");
});

test("setOtherReviewOpinion stores editable 其他意见 without switching to 命中", () => {
  const updated = setOtherReviewOpinion(
    {
      ...buildResult(),
      matches: [],
      categories: [],
      label: "其他",
    },
    "审核人补充：归类为其他",
  );

  assert.equal(updated.label, "其他");
  assert.equal(updated.matches.length, 1);
  assert.equal(updated.matches[0]?.type_code, "OTHER");
  assert.equal(updated.matches[0]?.reason, "审核人补充：归类为其他");
});

test("adding another 其他 row replaces the prior OTHER row instead of duplicating it", () => {
  const initial = addManualReviewMatch(
    {
      ...buildResult(),
      matches: [],
      categories: [],
      label: "其他",
    },
    buildManualReviewMatch({
      entryId: "manual-other-1",
      category: "其他",
      text: "未命中知识库条目，归类为其他。",
      typeCode: "OTHER",
      reason: "第一次意见",
    }),
  );

  const updated = addManualReviewMatch(
    initial,
    buildManualReviewMatch({
      entryId: "manual-other-2",
      category: "其他",
      text: "未命中知识库条目，归类为其他。",
      typeCode: "OTHER",
      reason: "第二次意见",
    }),
  );

  assert.equal(updated.matches.length, 1);
  assert.equal(updated.matches[0]?.entry_id, "manual-other-2");
  assert.equal(updated.matches[0]?.reason, "第二次意见");
});

test("adding a knowledge-base hit clears stale 其他 placeholders", () => {
  const initial = setOtherReviewOpinion(
    {
      ...buildResult(),
      matches: [],
      categories: [],
      label: "其他",
    },
    "暂时归为其他",
  );

  const updated = addManualReviewMatch(
    initial,
    buildManualReviewMatch({
      entryId: "manual-hit-1",
      category: "分类C",
      text: "补充命中条目",
      typeCode: "C",
      reason: "补充命中意见",
    }),
  );

  assert.equal(updated.label, "命中");
  assert.equal(updated.matches.length, 1);
  assert.equal(updated.matches[0]?.entry_id, "manual-hit-1");
  assert.deepEqual(updated.categories, ["分类C"]);
});

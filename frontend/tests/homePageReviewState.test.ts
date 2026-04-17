import assert from "node:assert/strict";
import test from "node:test";

import {
  markCompareRowReviewed,
  normalizeCompareRow,
  removeCompareRow,
  updateCompareRowReviewComment,
} from "../src/pages/homePageReviewState.ts";
import type { CompareRow } from "../src/types";

function buildRow(): CompareRow {
  return {
    row_id: "row-1",
    chapter_title: "1.1",
    source_excerpt: "source",
    kb_entry_id: "kb-1",
    kb_entry_text: "标准条目",
    difference_summary_brief: "需要澄清。",
    difference_summary: "存在冲突：需要澄清。",
    type_code: "P",
    review_comment: "",
    review_status: "未审",
  };
}

test("normalizeCompareRow defaults missing review state to 未审", () => {
  const normalized = normalizeCompareRow({
    ...buildRow(),
    review_status: undefined as unknown as "已审" | "未审",
  });

  assert.equal(normalized.review_status, "未审");
});

test("markCompareRowReviewed flips the review status to 已审", () => {
  const reviewed = markCompareRowReviewed(buildRow());

  assert.equal(reviewed.review_status, "已审");
});

test("updating review comment resets the row to 未审", () => {
  const updated = updateCompareRowReviewComment(
    markCompareRowReviewed(buildRow()),
    "人工审核意见",
  );

  assert.equal(updated.review_status, "未审");
  assert.equal(updated.review_comment, "人工审核意见");
});

test("removeCompareRow deletes the targeted row", () => {
  const updated = removeCompareRow(
    [buildRow(), { ...buildRow(), row_id: "row-2", type_code: "A" }],
    "row-1",
  );

  assert.deepEqual(updated.map((row) => row.row_id), ["row-2"]);
});

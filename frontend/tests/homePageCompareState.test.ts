import assert from "node:assert/strict";
import test from "node:test";

import {
  buildTypeFilterModel,
  filterCompareRowsByType,
  mergeCompareRow,
} from "../src/pages/homePageCompareState.ts";
import type { CompareRow } from "../src/types";

function buildRow(rowId: string, typeCode: CompareRow["type_code"]): CompareRow {
  return {
    row_id: rowId,
    chapter_title: "1 总则",
    source_excerpt: `source-${rowId}`,
    kb_entry_id: `kb-${rowId}`,
    kb_entry_text: "标准条目",
    difference_summary: "部分满足：需要澄清。",
    type_code: typeCode,
    review_comment: "",
    review_status: "未审",
  };
}

test("type filters keep ALL P A B C ordering and never expose OTHER", () => {
  const model = buildTypeFilterModel([
    buildRow("row-1", "P"),
    buildRow("row-2", "A"),
    buildRow("row-3", "C"),
  ]);

  assert.deepEqual(model.order, ["ALL", "P", "A", "B", "C"]);
  assert.equal(model.counts.ALL, 3);
  assert.equal(model.counts.P, 1);
  assert.equal(model.counts.A, 1);
  assert.equal(model.counts.B, 0);
  assert.equal(model.counts.C, 1);
  assert.equal("OTHER" in model.counts, false);
});

test("filterCompareRowsByType returns all rows for ALL and exact type matches otherwise", () => {
  const rows = [
    buildRow("row-1", "P"),
    buildRow("row-2", "A"),
    buildRow("row-3", "P"),
  ];

  assert.equal(filterCompareRowsByType(rows, "ALL").length, 3);
  assert.deepEqual(
    filterCompareRowsByType(rows, "P").map((row) => row.row_id),
    ["row-1", "row-3"],
  );
});

test("mergeCompareRow replaces an existing row with the same row_id", () => {
  const merged = mergeCompareRow(
    [buildRow("row-1", "P")],
    {
      ...buildRow("row-1", "A"),
      difference_summary: "存在冲突：需要澄清。",
    },
  );

  assert.equal(merged.length, 1);
  assert.equal(merged[0]?.type_code, "A");
  assert.equal(merged[0]?.difference_summary, "存在冲突：需要澄清。");
});

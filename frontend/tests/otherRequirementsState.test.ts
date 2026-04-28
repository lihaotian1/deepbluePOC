import assert from "node:assert/strict";
import test from "node:test";

import {
  OTHER_REQUIREMENTS_PAGE_SIZE,
  buildOtherRequirementsPageModel,
  canOpenOtherRequirements,
  mergeOtherRequirementRow,
} from "../src/pages/otherRequirementsState.ts";
import type { OtherRequirementRow } from "../src/types";

function buildRow(rowId: string, sourceOrder: number): OtherRequirementRow {
  return {
    row_id: rowId,
    chapter_title: "3 参数",
    source_excerpt: `source-${rowId}`,
    summary: `询价文件要求提供 ${rowId}`,
    source_order: sourceOrder,
  };
}

test("mergeOtherRequirementRow replaces duplicate row ids and keeps source order ascending", () => {
  const merged = mergeOtherRequirementRow(
    [buildRow("row-2", 2), buildRow("row-1", 1)],
    {
      ...buildRow("row-2", 4),
      summary: "updated",
    },
  );

  assert.deepEqual(merged.map((row) => row.row_id), ["row-1", "row-2"]);
  assert.equal(merged[1]?.summary, "updated");
  assert.equal(merged[1]?.source_order, 4);
});

test("buildOtherRequirementsPageModel paginates with the fixed page size and clamps page bounds", () => {
  const rows = Array.from({ length: OTHER_REQUIREMENTS_PAGE_SIZE + 3 }, (_, index) => buildRow(`row-${index + 1}`, index + 1));
  const model = buildOtherRequirementsPageModel(rows, 99, OTHER_REQUIREMENTS_PAGE_SIZE);

  assert.equal(model.totalItems, OTHER_REQUIREMENTS_PAGE_SIZE + 3);
  assert.equal(model.totalPages, 2);
  assert.equal(model.page, 2);
  assert.equal(model.rows.length, 3);
  assert.deepEqual(
    model.rows.map((row) => row.row_id),
    ["row-11", "row-12", "row-13"],
  );
});

test("canOpenOtherRequirements only allows opening when rows exist and parsing is idle", () => {
  assert.equal(canOpenOtherRequirements([], false), false);
  assert.equal(canOpenOtherRequirements([buildRow("row-1", 1)], true), false);
  assert.equal(canOpenOtherRequirements([buildRow("row-1", 1)], false), true);
});

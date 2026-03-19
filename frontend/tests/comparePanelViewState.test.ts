import assert from "node:assert/strict";
import test from "node:test";

import {
  buildComparePanelActionButtons,
  getVisibleComparePanelLogs,
  resolveComparePanelProgressPercent,
  shouldKeepComparePanelLogPinnedToBottom,
} from "../src/components/comparePanelViewState.ts";

test("all compare panel actions use the shared fixed-size class", () => {
  const buttons = buildComparePanelActionButtons(false);

  assert.equal(buttons.length, 3);
  assert.ok(buttons.every((button) => button.className.includes("compare-panel__action-btn")));
});

test("submit review uses a distinct visual variant from export", () => {
  const buttons = buildComparePanelActionButtons(false);
  const exportButton = buttons.find((button) => button.key === "export");
  const submitButton = buttons.find((button) => button.key === "submit-review");

  assert.ok(exportButton);
  assert.ok(submitButton);
  assert.notEqual(exportButton?.className, submitButton?.className);
});

test("compare panel primary action uses smart-analysis wording", () => {
  const idleButton = buildComparePanelActionButtons(false).find((button) => button.key === "compare");
  const runningButton = buildComparePanelActionButtons(true).find((button) => button.key === "compare");

  assert.equal(idleButton?.label, "开始智能分析");
  assert.equal(runningButton?.label, "智能分析中...");
});

test("compare panel keeps the complete log history visible to the scroll area", () => {
  const logs = Array.from({ length: 12 }, (_, index) => `log-${index + 1}`);

  assert.deepEqual(getVisibleComparePanelLogs(logs), logs);
});

test("compare panel keeps the newest logs visible when the user is already near the bottom", () => {
  assert.equal(
    shouldKeepComparePanelLogPinnedToBottom({
      scrollTop: 126,
      clientHeight: 170,
      scrollHeight: 300,
    }),
    true,
  );
});

test("compare panel respects manual scrolling away from the bottom", () => {
  assert.equal(
    shouldKeepComparePanelLogPinnedToBottom({
      scrollTop: 20,
      clientHeight: 170,
      scrollHeight: 300,
    }),
    false,
  );
});

test("compare panel progress percent stays at zero without a valid total", () => {
  assert.equal(resolveComparePanelProgressPercent(0, 0), 0);
  assert.equal(resolveComparePanelProgressPercent(3, 0), 0);
});

test("compare panel progress percent reflects active chunk progress", () => {
  assert.equal(resolveComparePanelProgressPercent(2, 5), 40);
});

test("compare panel progress percent caps at one hundred", () => {
  assert.equal(resolveComparePanelProgressPercent(5, 5), 100);
  assert.equal(resolveComparePanelProgressPercent(8, 5), 100);
});

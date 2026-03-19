import assert from "node:assert/strict";
import test from "node:test";

import {
  buildComparePanelActionButtons,
  getVisibleComparePanelLogs,
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

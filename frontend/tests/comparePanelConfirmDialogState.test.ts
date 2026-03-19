import assert from "node:assert/strict";
import test from "node:test";

import { getComparePanelConfirmDialogState } from "../src/components/comparePanelConfirmDialogState.ts";

test("submit review confirm dialog uses the shared centered modal shell", () => {
  const state = getComparePanelConfirmDialogState(true);

  assert.equal(state.isOpen, true);
  assert.equal(state.backdropClassName, "modal-backdrop");
  assert.equal(state.dialogClassName, "modal-card compare-panel__confirm-dialog");
  assert.equal(state.title, "提交审核");
  assert.equal(state.confirmLabel, "确定");
  assert.equal(state.cancelLabel, "取消");
  assert.match(state.message, /是否提交该文档的偏差分析/);
});

test("closed confirm dialog state stays hidden", () => {
  const state = getComparePanelConfirmDialogState(false);

  assert.equal(state.isOpen, false);
});

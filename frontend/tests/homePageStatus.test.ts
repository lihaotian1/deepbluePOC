import assert from "node:assert/strict";
import test from "node:test";

import { buildCompareDoneMessage, resolveHomePageStatusDotClass } from "../src/pages/homePageStatus.ts";

test("buildCompareDoneMessage renders the delivered completion copy", () => {
  assert.equal(buildCompareDoneMessage(0), "全部解析完毕，已生成 0 条结果");
  assert.equal(buildCompareDoneMessage(12), "全部解析完毕，已生成 12 条结果");
});

test("resolveHomePageStatusDotClass uses animated status while parsing and static status afterwards", () => {
  assert.equal(resolveHomePageStatusDotClass("running"), "pulse-dot");
  assert.equal(resolveHomePageStatusDotClass("done"), "pulse-dot pulse-dot--static");
  assert.equal(resolveHomePageStatusDotClass("idle"), "pulse-dot pulse-dot--static");
  assert.equal(resolveHomePageStatusDotClass("error"), "pulse-dot pulse-dot--static");
});

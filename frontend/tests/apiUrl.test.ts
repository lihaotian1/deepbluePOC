import assert from "node:assert/strict";
import test from "node:test";

import { buildAssetUrl, normalizeApiBase, resolveServerBase } from "../src/api/url.ts";

test("defaults API requests to the same-origin proxy path", () => {
  assert.equal(normalizeApiBase(undefined), "/api/v1");
  assert.equal(normalizeApiBase("   "), "/api/v1");
});

test("preserves explicit external backend origins", () => {
  assert.equal(normalizeApiBase("http://43.138.48.80:8000/api/v1"), "http://43.138.48.80:8000/api/v1");
});

test("builds asset URLs without falling back to localhost", () => {
  assert.equal(resolveServerBase("/api/v1"), "");
  assert.equal(buildAssetUrl("/api/v1", "/assets/logo/logo.png"), "/assets/logo/logo.png");
  assert.equal(
    buildAssetUrl("http://43.138.48.80:8000/api/v1", "/assets/logo/logo.png"),
    "http://43.138.48.80:8000/assets/logo/logo.png",
  );
});

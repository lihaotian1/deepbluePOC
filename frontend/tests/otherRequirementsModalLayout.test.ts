import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const themeCss = readFileSync(new URL("../src/styles/theme.css", import.meta.url), "utf8");

test("other requirements modal uses a centered 80 percent viewport layout", () => {
  assert.match(themeCss, /\.other-requirements-modal\s*\{[\s\S]*?width:\s*min\(80vw,\s*1280px\);/);
  assert.match(themeCss, /\.other-requirements-modal\s*\{[\s\S]*?height:\s*80vh;/);
});

test("other requirements table keeps the requested three-column distribution", () => {
  assert.match(themeCss, /\.other-requirements-table th:nth-child\(1\),[\s\S]*?width:\s*10%;/);
  assert.match(themeCss, /\.other-requirements-table th:nth-child\(2\),[\s\S]*?width:\s*54%;/);
  assert.match(themeCss, /\.other-requirements-table th:nth-child\(3\),[\s\S]*?width:\s*36%;/);
});

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const themeCss = readFileSync(new URL("../src/styles/theme.css", import.meta.url), "utf8");

test("results table keeps the requested column width distribution", () => {
  assert.match(themeCss, /\.results-table th:nth-child\(1\),[\s\S]*?width: 13%;/);
  assert.match(themeCss, /\.results-table th:nth-child\(2\),[\s\S]*?width: 29%;/);
  assert.match(themeCss, /\.results-table th:nth-child\(3\),[\s\S]*?width: 29%;/);
  assert.match(themeCss, /\.results-table th:nth-child\(4\),[\s\S]*?width: 21%;/);
  assert.match(themeCss, /\.results-table th:nth-child\(5\),[\s\S]*?width: 8%;/);
});

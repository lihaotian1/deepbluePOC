import assert from "node:assert/strict";
import test from "node:test";

import packageJson from "../package.json" with { type: "json" };

function parseMajor(versionRange: string | undefined) {
  const match = versionRange?.match(/(\d+)/);
  return match ? Number(match[1]) : NaN;
}

test("vite major version stays compatible with @vitejs/plugin-react v4 peer range", () => {
  const viteVersion = packageJson.devDependencies?.vite;
  const pluginReactVersion = packageJson.devDependencies?.["@vitejs/plugin-react"];

  assert.equal(parseMajor(pluginReactVersion), 4);
  assert.ok(parseMajor(viteVersion) <= 7, `Expected vite <= 7 for plugin-react v4, got ${viteVersion}`);
});

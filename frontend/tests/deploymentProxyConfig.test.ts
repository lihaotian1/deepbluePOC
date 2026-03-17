import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import viteConfig from "../vite.config.ts";

test("vite dev server proxies API and logo requests to the backend", async () => {
  const resolved = typeof viteConfig === "function" ? await viteConfig({ command: "serve", mode: "development" }) : viteConfig;
  const proxy = resolved.server?.proxy;

  assert.ok(proxy);
  assert.equal(proxy["/api"]?.target, "http://localhost:8000");
  assert.equal(proxy["/assets/logo"]?.target, "http://localhost:8000");
});

test("nginx only forwards backend-owned asset paths", () => {
  const config = readFileSync(new URL("../nginx.conf", import.meta.url), "utf8");

  assert.match(config, /location \/api\//);
  assert.match(config, /location \/assets\/logo\//);
  assert.doesNotMatch(config, /location \/assets\/ \{/);
});

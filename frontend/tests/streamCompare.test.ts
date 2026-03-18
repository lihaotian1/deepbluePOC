import assert from "node:assert/strict";
import test from "node:test";

import { streamCompare } from "../src/api/sse.ts";

test("streamCompare retries one transport failure and then succeeds", async () => {
  const seenCalls: number[] = [];
  const seenEvents: Array<{ eventName: string; data: unknown }> = [];
  const seenErrors: string[] = [];
  const seenRetries: string[] = [];
  let attempts = 0;

  await streamCompare(
    "doc-1",
    ["标准化配套知识库.json"],
    (eventName, data) => {
      seenEvents.push({ eventName, data });
    },
    (message) => {
      seenErrors.push(message);
    },
    {
      fetchEventSourceImpl: async (_url, handlers) => {
        attempts += 1;
        seenCalls.push(attempts);
        if (attempts === 1) {
          handlers.onerror?.(new TypeError("network error"));
          return;
        }

        handlers.onmessage?.({ event: "chunk_result", data: JSON.stringify({ chunk_id: 1 }) });
      },
      onRetry: (message) => {
        seenRetries.push(message);
      },
    },
  );

  assert.deepEqual(seenCalls, [1, 2]);
  assert.equal(seenEvents.length, 1);
  assert.equal(seenEvents[0].eventName, "chunk_result");
  assert.deepEqual(seenRetries, ["流式连接中断，正在自动重试(1/1)..."]);
  assert.deepEqual(seenErrors, ["流式处理异常: TypeError: network error"]);
});

test("streamCompare rejects after the retry budget is exhausted", async () => {
  const seenRetries: string[] = [];

  await assert.rejects(
    () =>
      streamCompare(
        "doc-1",
        ["标准化配套知识库.json"],
        () => undefined,
        () => undefined,
        {
          fetchEventSourceImpl: async (_url, handlers) => {
            handlers.onerror?.(new TypeError("network error"));
          },
          onRetry: (message) => {
            seenRetries.push(message);
          },
        },
      ),
    /network error/,
  );

  assert.deepEqual(seenRetries, ["流式连接中断，正在自动重试(1/1)..."]);
});

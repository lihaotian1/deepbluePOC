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

        handlers.onmessage?.({ event: "compare_row", data: JSON.stringify({ row_id: "row-1" }) });
      },
      onRetry: (message) => {
        seenRetries.push(message);
      },
    },
  );

  assert.deepEqual(seenCalls, [1, 2]);
  assert.equal(seenEvents.length, 1);
  assert.equal(seenEvents[0].eventName, "compare_row");
  assert.deepEqual(seenRetries, ["流式连接中断，正在自动重试(1/1)..."]);
  assert.deepEqual(seenErrors, ["流式处理异常: TypeError: network error"]);
});

test("streamCompare rejects after the retry budget is exhausted", async () => {
  const seenRetries: string[] = [];

  await assert.rejects(
    () =>
      streamCompare(
        "doc-1",
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

test("streamCompare forwards other requirement events without rewriting the event name", async () => {
  const seenEvents: Array<{ eventName: string; data: unknown }> = [];

  await streamCompare(
    "doc-1",
    (eventName, data) => {
      seenEvents.push({ eventName, data });
    },
    () => undefined,
    {
      fetchEventSourceImpl: async (_url, handlers) => {
        handlers.onmessage?.({
          event: "other_requirement_row",
          data: JSON.stringify({ row_id: "other-1", source_excerpt: "Pump flow shall be 120 m3/h." }),
        });
      },
      maxRetries: 0,
    },
  );

  assert.deepEqual(seenEvents, [
    {
      eventName: "other_requirement_row",
      data: {
        row_id: "other-1",
        source_excerpt: "Pump flow shall be 120 m3/h.",
      },
    },
  ]);
});

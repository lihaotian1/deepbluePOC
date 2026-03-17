import { fetchEventSource } from "@microsoft/fetch-event-source";

import { getApiBase } from "./client";

type EventHandler = (eventName: string, data: unknown) => void;

export async function streamCompare(
  docId: string,
  knowledgeBaseFiles: string[],
  onEvent: EventHandler,
  onError: (message: string) => void
): Promise<void> {
  const url = `${getApiBase()}/documents/${docId}/compare/stream`;

  await fetchEventSource(url, {
    method: "POST",
    headers: {
      Accept: "text/event-stream",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ knowledge_base_files: knowledgeBaseFiles }),
    openWhenHidden: true,
    async onopen(response) {
      if (!response.ok) {
        throw new Error(`SSE open failed: ${response.status}`);
      }
    },
    onmessage(message) {
      try {
        const payload = message.data ? JSON.parse(message.data) : {};
        onEvent(message.event || "message", payload);
      } catch (error) {
        onError(`解析流式消息失败: ${String(error)}`);
      }
    },
    onerror(error) {
      onError(`流式处理异常: ${String(error)}`);
      throw error;
    },
  });
}

import { fetchEventSource } from "@microsoft/fetch-event-source";

type EventHandler = (eventName: string, data: unknown) => void;
type FetchEventSourceImpl = typeof fetchEventSource;

interface StreamCompareOptions {
  fetchEventSourceImpl?: FetchEventSourceImpl;
  onRetry?: (message: string) => void;
  maxRetries?: number;
}

export async function streamCompare(
  docId: string,
  knowledgeBaseFiles: string[],
  onEvent: EventHandler,
  onError: (message: string) => void,
  options: StreamCompareOptions = {},
): Promise<void> {
  const apiBase = normalizeSseApiBase((import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env?.VITE_API_BASE_URL);
  const url = `${apiBase}/documents/${docId}/compare/stream`;
  const fetchEventSourceImpl = options.fetchEventSourceImpl ?? fetchEventSource;
  const maxRetries = options.maxRetries ?? 1;
  let attempt = 0;

  while (true) {
    try {
      await fetchEventSourceImpl(url, {
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
      return;
    } catch (error) {
      if (attempt >= maxRetries || !(error instanceof TypeError)) {
        throw error;
      }

      attempt += 1;
      options.onRetry?.(`流式连接中断，正在自动重试(${attempt}/${maxRetries})...`);
    }
  }
}

function normalizeSseApiBase(apiBase?: string): string {
  const trimmed = apiBase?.trim();
  if (!trimmed) {
    return "/api/v1";
  }

  return trimmed.replace(/\/+$/, "");
}

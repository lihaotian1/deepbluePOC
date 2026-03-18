export interface ComparePanelActionButton {
  key: "compare" | "export" | "submit-review";
  label: string;
  className: string;
}

export function buildComparePanelActionButtons(comparing: boolean): ComparePanelActionButton[] {
  return [
    {
      key: "compare",
      label: comparing ? "比对中..." : "比对知识库",
      className: "btn btn-primary compare-panel__action-btn",
    },
    {
      key: "export",
      label: "导出 Excel",
      className: "btn btn-secondary compare-panel__action-btn",
    },
    {
      key: "submit-review",
      label: "提交审核",
      className: "btn btn-review compare-panel__action-btn",
    },
  ];
}

export function getVisibleComparePanelLogs(logs: string[]) {
  return logs;
}

interface ComparePanelLogMetrics {
  scrollTop: number;
  clientHeight: number;
  scrollHeight: number;
}

export function shouldKeepComparePanelLogPinnedToBottom(metrics: ComparePanelLogMetrics) {
  const distanceFromBottom = metrics.scrollHeight - (metrics.scrollTop + metrics.clientHeight);
  return distanceFromBottom <= 12;
}

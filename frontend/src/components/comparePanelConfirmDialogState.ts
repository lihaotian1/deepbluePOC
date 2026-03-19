export interface ComparePanelConfirmDialogState {
  isOpen: boolean;
  backdropClassName: string;
  dialogClassName: string;
  title: string;
  message: string;
  confirmLabel: string;
  cancelLabel: string;
}

export function getComparePanelConfirmDialogState(isOpen: boolean): ComparePanelConfirmDialogState {
  return {
    isOpen,
    backdropClassName: "modal-backdrop",
    dialogClassName: "modal-card compare-panel__confirm-dialog",
    title: "提交审核",
    message: "是否提交该文档的偏差分析，提交后将流转给XXX进行审核。",
    confirmLabel: "确定",
    cancelLabel: "取消",
  };
}

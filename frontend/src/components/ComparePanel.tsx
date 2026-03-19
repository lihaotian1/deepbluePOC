import { useCallback, useEffect, useRef, useState, type KeyboardEvent as ReactKeyboardEvent } from "react";
import { createPortal } from "react-dom";

import type { KnowledgeBaseFileSummary } from "../types";
import { getComparePanelConfirmDialogState } from "./comparePanelConfirmDialogState";
import {
  buildComparePanelActionButtons,
  getVisibleComparePanelLogs,
  resolveComparePanelProgressPercent,
  shouldKeepComparePanelLogPinnedToBottom,
} from "./comparePanelViewState";

function lockGlobalModalScroll() {
  if (typeof document === "undefined") {
    return;
  }

  const body = document.body;
  const currentCount = Number(body.dataset.modalLockCount ?? "0");
  body.dataset.modalLockCount = `${currentCount + 1}`;
  body.classList.add("has-modal-open");
}

function unlockGlobalModalScroll() {
  if (typeof document === "undefined") {
    return;
  }

  const body = document.body;
  const currentCount = Number(body.dataset.modalLockCount ?? "0");
  const nextCount = Math.max(0, currentCount - 1);

  if (nextCount === 0) {
    delete body.dataset.modalLockCount;
    body.classList.remove("has-modal-open");
    return;
  }

  body.dataset.modalLockCount = `${nextCount}`;
}

function focusFirstModalElement(container: HTMLElement | null) {
  if (!container) {
    return;
  }

  const focusableElements = Array.from(
    container.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  );

  if (focusableElements.length) {
    focusableElements[0].focus();
    return;
  }

  container.focus();
}

function trapFocusWithinModal(event: ReactKeyboardEvent<HTMLElement>, container: HTMLElement | null) {
  if (event.key !== "Tab" || !container) {
    return;
  }

  const focusableElements = Array.from(
    container.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  );

  if (!focusableElements.length) {
    event.preventDefault();
    container.focus();
    return;
  }

  const firstElement = focusableElements[0];
  const lastElement = focusableElements[focusableElements.length - 1];
  const activeElement = document.activeElement;

  if (event.shiftKey && activeElement === firstElement) {
    event.preventDefault();
    lastElement.focus();
    return;
  }

  if (!event.shiftKey && activeElement === lastElement) {
    event.preventDefault();
    firstElement.focus();
  }
}

interface ComparePanelProps {
  hasDocument: boolean;
  comparing: boolean;
  progressText: string;
  progressCurrent: number;
  progressTotal: number;
  logs: string[];
  knowledgeBaseOptions: KnowledgeBaseFileSummary[];
  selectedKnowledgeBaseFiles: string[];
  submittedForReview: boolean;
  onToggleKnowledgeBase: (fileName: string) => void;
  onCompare: () => void;
  onExport: () => void;
  onSubmitReview: () => void;
}

function ComparePanel(props: ComparePanelProps) {
  const {
    hasDocument,
    comparing,
    progressText,
    progressCurrent,
    progressTotal,
    logs,
    knowledgeBaseOptions,
    selectedKnowledgeBaseFiles,
    submittedForReview,
    onToggleKnowledgeBase,
    onCompare,
    onExport,
    onSubmitReview,
  } = props;
  const actionButtons = buildComparePanelActionButtons(comparing);
  const visibleLogs = getVisibleComparePanelLogs(logs);
  const progressPercent = resolveComparePanelProgressPercent(progressCurrent, progressTotal);
  const [isSubmitDialogOpen, setIsSubmitDialogOpen] = useState(false);
  const logRef = useRef<HTMLDivElement | null>(null);
  const submitDialogRef = useRef<HTMLElement | null>(null);
  const logScrollCleanupRef = useRef<(() => void) | null>(null);
  const shouldAutoScrollRef = useRef(true);
  const submitDialog = getComparePanelConfirmDialogState(isSubmitDialogOpen);

  const setLogRef = useCallback((node: HTMLDivElement | null) => {
    if (logScrollCleanupRef.current) {
      logScrollCleanupRef.current();
      logScrollCleanupRef.current = null;
    }

    logRef.current = node;
    if (!node) {
      return;
    }

    const updatePinnedState = () => {
      shouldAutoScrollRef.current = shouldKeepComparePanelLogPinnedToBottom({
        scrollTop: node.scrollTop,
        clientHeight: node.clientHeight,
        scrollHeight: node.scrollHeight,
      });
    };

    updatePinnedState();
    node.addEventListener("scroll", updatePinnedState);
    logScrollCleanupRef.current = () => node.removeEventListener("scroll", updatePinnedState);
  }, []);

  useEffect(() => {
    return () => {
      if (logScrollCleanupRef.current) {
        logScrollCleanupRef.current();
      }
    };
  }, []);

  useEffect(() => {
    if (!isSubmitDialogOpen) {
      return;
    }

    lockGlobalModalScroll();
    return () => unlockGlobalModalScroll();
  }, [isSubmitDialogOpen]);

  useEffect(() => {
    if (!isSubmitDialogOpen) {
      return;
    }

    focusFirstModalElement(submitDialogRef.current);
  }, [isSubmitDialogOpen]);

  useEffect(() => {
    const logContainer = logRef.current;
    if (!logContainer) {
      return;
    }

    if (shouldAutoScrollRef.current) {
      logContainer.scrollTop = logContainer.scrollHeight;
    }
  }, [visibleLogs]);

  function handleOpenSubmitDialog() {
    setIsSubmitDialogOpen(true);
  }

  function handleCloseSubmitDialog() {
    setIsSubmitDialogOpen(false);
  }

  function handleConfirmSubmitDialog() {
    setIsSubmitDialogOpen(false);
    void onSubmitReview();
  }

  return (
    <section className="glass-card compare-panel">
      <div className="compare-panel__head">
        <h2>知识库智能分析</h2>
        <p>默认使用标准化配套知识库进行智能分析，可按需追加投标说明知识库。</p>
      </div>

      <div className="compare-panel__selector-group">
        <span className="compare-panel__selector-label">本次智能分析范围</span>
        <div className="compare-panel__selector-list">
          {knowledgeBaseOptions.map((option) => {
            const checked = selectedKnowledgeBaseFiles.includes(option.file_name);
            const disableToggle = checked && selectedKnowledgeBaseFiles.length === 1;

            return (
              <label
                key={option.file_name}
                className={`compare-panel__selector ${checked ? "is-selected" : ""} ${disableToggle ? "is-locked" : ""}`}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  disabled={comparing}
                  onChange={() => onToggleKnowledgeBase(option.file_name)}
                />
                <span>{option.display_name}</span>
              </label>
            );
          })}
        </div>
      </div>

      <div className="compare-panel__actions">
        <button className={actionButtons[0].className} onClick={onCompare} disabled={!hasDocument || comparing || !selectedKnowledgeBaseFiles.length}>
          {actionButtons[0].label}
        </button>
        <button className={actionButtons[1].className} onClick={onExport} disabled={!hasDocument || comparing}>
          {actionButtons[1].label}
        </button>
        <button className={actionButtons[2].className} onClick={handleOpenSubmitDialog} disabled={!hasDocument || comparing}>
          {actionButtons[2].label}
        </button>
        {submittedForReview ? <span className="compare-panel__submitted">已提交</span> : null}
      </div>

      <div className="compare-panel__status">
        <span className="pulse-dot" />
        <span
          className="compare-panel__status-progress"
          role="progressbar"
          aria-label="智能分析进度"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={progressPercent}
        >
          <span className="compare-panel__status-progress-fill" style={{ width: `${progressPercent}%` }} />
        </span>
        <span>{progressText}</span>
      </div>

      {!!visibleLogs.length && (
        <div className="compare-panel__log" ref={setLogRef}>
          {visibleLogs.map((line, index) => (
            <p key={`${line}-${index}`}>{line}</p>
          ))}
        </div>
      )}

      {typeof document !== "undefined" && submitDialog.isOpen
        ? createPortal(
            <div className={submitDialog.backdropClassName} role="presentation" onClick={handleCloseSubmitDialog}>
              <section
                ref={submitDialogRef}
                className={submitDialog.dialogClassName}
                role="dialog"
                aria-modal="true"
                tabIndex={-1}
                onClick={(event) => event.stopPropagation()}
                onKeyDown={(event) => trapFocusWithinModal(event, submitDialogRef.current)}
                onWheelCapture={(event) => event.stopPropagation()}
              >
                <div className="modal-card__head compare-panel__confirm-head">
                  <div>
                    <h4>{submitDialog.title}</h4>
                  </div>
                </div>
                <div className="compare-panel__confirm-body">
                  <p className="compare-panel__confirm-text">{submitDialog.message}</p>
                  <div className="modal-card__actions compare-panel__confirm-actions">
                    <button className="btn btn-lite" type="button" onClick={handleCloseSubmitDialog}>
                      {submitDialog.cancelLabel}
                    </button>
                    <button className="btn btn-review" type="button" onClick={handleConfirmSubmitDialog}>
                      {submitDialog.confirmLabel}
                    </button>
                  </div>
                </div>
              </section>
            </div>,
            document.body,
          )
        : null}
    </section>
  );
}

export default ComparePanel;

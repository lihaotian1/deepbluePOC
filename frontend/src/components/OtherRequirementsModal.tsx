import { useEffect, useMemo, useRef } from "react";
import { createPortal } from "react-dom";

import type { OtherRequirementRow } from "../types";
import { buildOtherRequirementsPageModel, OTHER_REQUIREMENTS_PAGE_SIZE } from "../pages/otherRequirementsState";

interface OtherRequirementsModalProps {
  isOpen: boolean;
  rows: OtherRequirementRow[];
  page: number;
  onClose: () => void;
  onPageChange: (page: number) => void;
}

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

function OtherRequirementsModal(props: OtherRequirementsModalProps) {
  const { isOpen, rows, page, onClose, onPageChange } = props;
  const dialogRef = useRef<HTMLElement | null>(null);
  const pageModel = useMemo(
    () => buildOtherRequirementsPageModel(rows, page, OTHER_REQUIREMENTS_PAGE_SIZE),
    [page, rows],
  );

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    lockGlobalModalScroll();
    return () => unlockGlobalModalScroll();
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    focusFirstModalElement(dialogRef.current);
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    if (page !== pageModel.page) {
      onPageChange(pageModel.page);
    }
  }, [isOpen, onPageChange, page, pageModel.page]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (typeof document === "undefined" || !isOpen) {
    return null;
  }

  return createPortal(
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <section
        ref={dialogRef}
        className="modal-card other-requirements-modal"
        role="dialog"
        aria-modal="true"
        aria-label="其他要求"
        tabIndex={-1}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="modal-card__head">
          <div>
            <h4>其他要求</h4>
            <p>仅展示未命中标准化配套条目的技术要求，共 {pageModel.totalItems} 条。</p>
          </div>
          <div className="modal-card__actions">
            <button className="btn btn-lite" type="button" onClick={onClose}>
              关闭
            </button>
          </div>
        </div>

        <div className="other-requirements-modal__body">
          <div className="other-requirements-table-wrap">
            <table className="other-requirements-table">
              <thead>
                <tr>
                  <th>序号</th>
                  <th>询价文件最小原文</th>
                  <th>AI一句话总结</th>
                </tr>
              </thead>
              <tbody>
                {pageModel.rows.map((row, index) => (
                  <tr key={row.row_id}>
                    <td>{(pageModel.page - 1) * OTHER_REQUIREMENTS_PAGE_SIZE + index + 1}</td>
                    <td>{row.source_excerpt}</td>
                    <td>{row.summary}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="kb-pagination-bar other-requirements-pagination">
            <span>
              当前第 {pageModel.page}/{pageModel.totalPages} 页，共 {pageModel.totalItems} 条
            </span>
            <div className="kb-pagination-bar__actions">
              <button
                className="btn btn-lite"
                type="button"
                onClick={() => onPageChange(Math.max(1, pageModel.page - 1))}
                disabled={pageModel.page <= 1}
              >
                上一页
              </button>
              <button
                className="btn btn-lite"
                type="button"
                onClick={() => onPageChange(Math.min(pageModel.totalPages, pageModel.page + 1))}
                disabled={pageModel.page >= pageModel.totalPages}
              >
                下一页
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>,
    document.body,
  );
}

export default OtherRequirementsModal;

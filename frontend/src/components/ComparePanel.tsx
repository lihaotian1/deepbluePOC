import type { KnowledgeBaseFileSummary } from "../types";

interface ComparePanelProps {
  hasDocument: boolean;
  comparing: boolean;
  progressText: string;
  logs: string[];
  knowledgeBaseOptions: KnowledgeBaseFileSummary[];
  selectedKnowledgeBaseFiles: string[];
  onToggleKnowledgeBase: (fileName: string) => void;
  onCompare: () => void;
  onExport: () => void;
}

function ComparePanel(props: ComparePanelProps) {
  const {
    hasDocument,
    comparing,
    progressText,
    logs,
    knowledgeBaseOptions,
    selectedKnowledgeBaseFiles,
    onToggleKnowledgeBase,
    onCompare,
    onExport,
  } = props;

  return (
    <section className="glass-card compare-panel">
      <div className="compare-panel__head">
        <h2>知识库比对</h2>
        <p>默认比对标准化配套知识库，可按需追加投标说明知识库。</p>
      </div>

      <div className="compare-panel__selector-group">
        <span className="compare-panel__selector-label">本次比对范围</span>
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
        <button className="btn btn-primary" onClick={onCompare} disabled={!hasDocument || comparing || !selectedKnowledgeBaseFiles.length}>
          {comparing ? "比对中..." : "比对知识库"}
        </button>
        <button className="btn btn-secondary" onClick={onExport} disabled={!hasDocument || comparing}>
          导出 Excel
        </button>
      </div>

      <div className="compare-panel__status">
        <span className="pulse-dot" />
        <span>{progressText}</span>
      </div>

      {!!logs.length && (
        <div className="compare-panel__log">
          {logs.slice(-8).map((line, index) => (
            <p key={`${line}-${index}`}>{line}</p>
          ))}
        </div>
      )}
    </section>
  );
}

export default ComparePanel;

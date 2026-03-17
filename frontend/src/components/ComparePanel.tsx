interface ComparePanelProps {
  hasDocument: boolean;
  comparing: boolean;
  progressText: string;
  logs: string[];
  onCompare: () => void;
  onExport: () => void;
}

function ComparePanel(props: ComparePanelProps) {
  const { hasDocument, comparing, progressText, logs, onCompare, onExport } = props;

  return (
    <section className="glass-card compare-panel">
      <div className="compare-panel__head">
        <h2>知识库比对</h2>
      </div>

      <div className="compare-panel__actions">
        <button className="btn btn-primary" onClick={onCompare} disabled={!hasDocument || comparing}>
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

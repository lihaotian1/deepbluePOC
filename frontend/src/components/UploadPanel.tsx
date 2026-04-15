interface UploadPanelProps {
  loading: boolean;
  fileName: string;
  onSelectFile: (file: File | null) => void;
  onSubmit: () => void;
}

function UploadPanel(props: UploadPanelProps) {
  const { loading, fileName, onSelectFile, onSubmit } = props;

  return (
    <section className="glass-card upload-panel">
      <div className="upload-panel__title-wrap">
        <h2>上传文件</h2>
      </div>

      <div className="upload-panel__controls">
        <label className="file-picker">
          <input
            type="file"
            accept=".pdf,.md,.txt,.docx"
            disabled={loading}
            onChange={(event) => onSelectFile(event.target.files?.[0] || null)}
          />
          <span>{fileName ? `已选择: ${fileName}` : "选择文件"}</span>
        </label>
        <button className="btn btn-primary" onClick={onSubmit} disabled={loading || !fileName}>
          {loading ? "上传中..." : "确定"}
        </button>
      </div>
    </section>
  );
}

export default UploadPanel;

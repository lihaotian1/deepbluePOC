import type { AppPage, KnowledgeBaseFileSummary } from "../types";

interface SidebarProps {
  logoUrl: string;
  currentPage: AppPage;
  kbFiles: KnowledgeBaseFileSummary[];
  selectedKbFile: string;
  onSelectPage: (page: AppPage) => void;
  onSelectKnowledgeBase: (fileName: string) => void;
}

function Sidebar(props: SidebarProps) {
  const {
    logoUrl,
    currentPage,
    kbFiles,
    selectedKbFile,
    onSelectPage,
    onSelectKnowledgeBase,
  } = props;

  const showKnowledgeList = currentPage === "knowledge-base" && kbFiles.length > 0;

  return (
    <aside className="app-sidebar">
      <div className="app-sidebar__top">
        <button type="button" className="sidebar-logo" onClick={() => onSelectPage("home")}>
          <img src={logoUrl} alt="logo" />
        </button>
      </div>

      <nav className="sidebar-nav">
        <button
          type="button"
          className={`sidebar-nav__item ${currentPage === "home" ? "is-active" : ""}`}
          onClick={() => onSelectPage("home")}
        >
          <HomeIcon />
          <span>主页</span>
        </button>

        <button
          type="button"
          className={`sidebar-nav__item ${currentPage === "knowledge-base" ? "is-active" : ""}`}
          onClick={() => onSelectPage("knowledge-base")}
        >
          <BookIcon />
          <span>知识库</span>
        </button>

        {showKnowledgeList ? (
          <div className="sidebar-submenu">
            {kbFiles.map((file) => (
              <button
                key={file.file_name}
                type="button"
                className={`sidebar-submenu__item ${selectedKbFile === file.file_name ? "is-active" : ""}`}
                onClick={() => onSelectKnowledgeBase(file.file_name)}
              >
                <FileIcon />
                <span>{file.display_name}</span>
              </button>
            ))}
          </div>
        ) : null}
      </nav>
    </aside>
  );
}

function HomeIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 11.5 12 5l8 6.5V20a1 1 0 0 1-1 1h-4v-6H9v6H5a1 1 0 0 1-1-1z" fill="currentColor" />
    </svg>
  );
}

function BookIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 0-3 3V4Zm3 2v12h9V7a1 1 0 0 0-1-1H8Zm-3 0v14a1 1 0 0 1 1-1h10" fill="currentColor" />
    </svg>
  );
}

function FileIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M7 3h7l5 5v13H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Zm6 2v4h4" fill="currentColor" />
    </svg>
  );
}

export default Sidebar;

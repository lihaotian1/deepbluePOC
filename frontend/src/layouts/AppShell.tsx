import { useEffect, useRef, type ReactNode } from "react";

import Sidebar from "../components/Sidebar";
import { getAppMainScrollResetKey, resetScrollableRegionToTop } from "./appMainScrollReset";
import type { AppPage, KnowledgeBaseFileSummary } from "../types";

interface AppShellProps {
  children: ReactNode;
  logoUrl: string;
  currentPage: AppPage;
  kbFiles: KnowledgeBaseFileSummary[];
  selectedKbFile: string;
  onSelectPage: (page: AppPage) => void;
  onSelectKnowledgeBase: (fileName: string) => void;
}

function AppShell(props: AppShellProps) {
  const mainRef = useRef<HTMLDivElement | null>(null);
  const {
    children,
    logoUrl,
    currentPage,
    kbFiles,
    selectedKbFile,
    onSelectPage,
    onSelectKnowledgeBase,
  } = props;
  const scrollResetKey = getAppMainScrollResetKey(currentPage, selectedKbFile);

  useEffect(() => {
    if (mainRef.current) {
      resetScrollableRegionToTop(mainRef.current);
    }
  }, [scrollResetKey]);

  return (
    <div className="app-shell">
      <Sidebar
        logoUrl={logoUrl}
        currentPage={currentPage}
        kbFiles={kbFiles}
        selectedKbFile={selectedKbFile}
        onSelectPage={onSelectPage}
        onSelectKnowledgeBase={onSelectKnowledgeBase}
      />
      <div ref={mainRef} className="app-main">
        {children}
      </div>
    </div>
  );
}

export default AppShell;

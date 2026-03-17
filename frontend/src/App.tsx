import { useEffect, useState } from "react";

import { getAssetUrl, listKnowledgeBases } from "./api/client";
import AppShell from "./layouts/AppShell";
import HomePage from "./pages/HomePage";
import KnowledgeBasePage from "./pages/KnowledgeBasePage";
import type { AppPage, KnowledgeBaseFileSummary } from "./types";

function App() {
  const [currentPage, setCurrentPage] = useState<AppPage>("home");
  const [kbFiles, setKbFiles] = useState<KnowledgeBaseFileSummary[]>([]);
  const [selectedKbFile, setSelectedKbFile] = useState("");
  const [hasVisitedKnowledgeBase, setHasVisitedKnowledgeBase] = useState(false);

  useEffect(() => {
    void refreshKnowledgeBases();
  }, []);

  async function refreshKnowledgeBases(preferredFile = "") {
    try {
      const files = await listKnowledgeBases();
      setKbFiles(files);
      setSelectedKbFile((current) => {
        if (preferredFile && files.some((file) => file.file_name === preferredFile)) {
          return preferredFile;
        }
        if (current && files.some((file) => file.file_name === current)) {
          return current;
        }
        return files[0]?.file_name || "";
      });
    } catch {
      setKbFiles([]);
      setSelectedKbFile("");
    }
  }

  function handleSelectPage(page: AppPage) {
    setCurrentPage(page);
    if (page === "knowledge-base" && !selectedKbFile && kbFiles.length > 0) {
      setSelectedKbFile(kbFiles[0].file_name);
    }
    if (page === "knowledge-base") {
      setHasVisitedKnowledgeBase(true);
    }
  }

  function handleSelectKnowledgeBase(fileName: string) {
    setHasVisitedKnowledgeBase(true);
    setCurrentPage("knowledge-base");
    setSelectedKbFile(fileName);
  }

  return (
    <AppShell
      logoUrl={getAssetUrl("/assets/logo/logo.png")}
      currentPage={currentPage}
      kbFiles={kbFiles}
      selectedKbFile={selectedKbFile}
      onSelectPage={handleSelectPage}
      onSelectKnowledgeBase={handleSelectKnowledgeBase}
    >
      <div className={`page-view ${currentPage === "home" ? "" : "is-hidden"}`} aria-hidden={currentPage !== "home"}>
        <HomePage />
      </div>
      {hasVisitedKnowledgeBase ? (
        <div
          className={`page-view ${currentPage === "knowledge-base" ? "" : "is-hidden"}`}
          aria-hidden={currentPage !== "knowledge-base"}
        >
          <KnowledgeBasePage
            selectedFile={selectedKbFile}
            onSelectFile={handleSelectKnowledgeBase}
            onFilesChanged={refreshKnowledgeBases}
          />
        </div>
      ) : null}
    </AppShell>
  );
}

export default App;

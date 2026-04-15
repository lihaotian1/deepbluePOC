import { useState } from "react";

import { getAssetUrl } from "./api/client";
import AppShell from "./layouts/AppShell";
import HomePage from "./pages/HomePage";
import KnowledgeBasePage from "./pages/KnowledgeBasePage";
import { STANDARD_KB_FILE_NAME } from "./pages/homePageCompareState";
import type { AppPage } from "./types";

function App() {
  const [currentPage, setCurrentPage] = useState<AppPage>("home");

  return (
    <AppShell
      logoUrl={getAssetUrl("/assets/logo/logo.png")}
      currentPage={currentPage}
      kbFiles={[]}
      selectedKbFile={STANDARD_KB_FILE_NAME}
      onSelectPage={setCurrentPage}
      onSelectKnowledgeBase={() => setCurrentPage("knowledge-base")}
    >
      <div className={`page-view ${currentPage === "home" ? "" : "is-hidden"}`} aria-hidden={currentPage !== "home"}>
        <HomePage />
      </div>
      <div
        className={`page-view ${currentPage === "knowledge-base" ? "" : "is-hidden"}`}
        aria-hidden={currentPage !== "knowledge-base"}
      >
        <KnowledgeBasePage />
      </div>
    </AppShell>
  );
}

export default App;

interface ScrollableRegion {
  scrollTop: number;
  scrollTo?: (options: { top: number }) => void;
}

export function getAppMainScrollResetKey(currentPage: string, selectedKbFile: string) {
  return `${currentPage}:${selectedKbFile}`;
}

export function resetScrollableRegionToTop(region: ScrollableRegion) {
  if (typeof region.scrollTo === "function") {
    region.scrollTo({ top: 0 });
    return;
  }

  region.scrollTop = 0;
}

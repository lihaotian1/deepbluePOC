interface ChunkCardModalStateInput {
  isReviewModalOpen: boolean;
  isAddModalOpen: boolean;
}

export function getChunkCardModalState(input: ChunkCardModalStateInput) {
  const hasAnyModalOpen = input.isReviewModalOpen || input.isAddModalOpen;
  const activeModalKey = input.isAddModalOpen ? "add" : input.isReviewModalOpen ? "review" : null;

  return {
    hasAnyModalOpen,
    activeModalKey,
    shouldLockBackgroundScroll: hasAnyModalOpen,
    reviewBackdropClassName: "modal-backdrop",
    addBackdropClassName: "modal-backdrop modal-backdrop--stacked",
    isReviewModalInert: input.isAddModalOpen,
  };
}

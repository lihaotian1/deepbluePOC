export type ChunkCardTranslationDotMode = "hidden" | "loading" | "ready";

export interface ChunkCardTranslationState {
  sourceSnapshot: string;
  requestedSourceSnapshot: string;
  translatedText: string;
  errorMessage: string;
  isShowingTranslation: boolean;
  isTranslating: boolean;
}

export interface ChunkCardTranslationView {
  buttonDisabled: boolean;
  buttonText: "翻译" | "原文";
  displayText: string;
  errorMessage: string;
  statusDotMode: ChunkCardTranslationDotMode;
}

export interface ChunkCardTranslationPayload {
  sourceSnapshot: string;
  translation: string;
}

export interface ChunkCardTranslationFailure {
  sourceSnapshot: string;
  message: string;
}

export function createChunkCardTranslationState(): ChunkCardTranslationState {
  return {
    sourceSnapshot: "",
    requestedSourceSnapshot: "",
    translatedText: "",
    errorMessage: "",
    isShowingTranslation: false,
    isTranslating: false,
  };
}

export function getChunkCardTranslationView(
  state: ChunkCardTranslationState,
  currentSourceText: string,
): ChunkCardTranslationView {
  const hasSourceText = !!currentSourceText.trim();

  if (state.isTranslating) {
    return {
      buttonDisabled: true,
      buttonText: "翻译",
      displayText: currentSourceText,
      errorMessage: "",
      statusDotMode: "loading",
    };
  }

  if (hasReusableChunkCardTranslation(state, currentSourceText) && state.isShowingTranslation) {
    return {
      buttonDisabled: false,
      buttonText: "原文",
      displayText: state.translatedText,
      errorMessage: "",
      statusDotMode: "ready",
    };
  }

  return {
    buttonDisabled: !hasSourceText,
    buttonText: "翻译",
    displayText: currentSourceText,
    errorMessage: state.errorMessage,
    statusDotMode: "hidden",
  };
}

export function hasReusableChunkCardTranslation(state: ChunkCardTranslationState, currentSourceText: string): boolean {
  return !!state.translatedText && state.sourceSnapshot === currentSourceText;
}

export function startChunkCardTranslation(
  state: ChunkCardTranslationState,
  sourceSnapshot: string,
): ChunkCardTranslationState {
  return {
    ...state,
    sourceSnapshot,
    requestedSourceSnapshot: sourceSnapshot,
    translatedText: state.sourceSnapshot === sourceSnapshot ? state.translatedText : "",
    errorMessage: "",
    isShowingTranslation: false,
    isTranslating: true,
  };
}

export function receiveChunkCardTranslationSuccess(
  state: ChunkCardTranslationState,
  payload: ChunkCardTranslationPayload,
): ChunkCardTranslationState {
  if (state.requestedSourceSnapshot !== payload.sourceSnapshot || state.sourceSnapshot !== payload.sourceSnapshot) {
    return state;
  }

  return {
    ...state,
    translatedText: payload.translation,
    errorMessage: "",
    isShowingTranslation: true,
    isTranslating: false,
  };
}

export function receiveChunkCardTranslationFailure(
  state: ChunkCardTranslationState,
  payload: ChunkCardTranslationFailure,
): ChunkCardTranslationState {
  if (state.requestedSourceSnapshot !== payload.sourceSnapshot || state.sourceSnapshot !== payload.sourceSnapshot) {
    return state;
  }

  return {
    ...state,
    translatedText: "",
    errorMessage: payload.message,
    isShowingTranslation: false,
    isTranslating: false,
  };
}

export function toggleChunkCardTranslationView(state: ChunkCardTranslationState): ChunkCardTranslationState {
  if (!state.translatedText || state.isTranslating) {
    return state;
  }

  return {
    ...state,
    errorMessage: "",
    isShowingTranslation: !state.isShowingTranslation,
  };
}

export function invalidateChunkCardTranslation(
  state: ChunkCardTranslationState,
  nextSourceSnapshot: string,
): ChunkCardTranslationState {
  if (state.sourceSnapshot === nextSourceSnapshot && state.requestedSourceSnapshot === nextSourceSnapshot) {
    return state;
  }

  return {
    sourceSnapshot: nextSourceSnapshot,
    requestedSourceSnapshot: nextSourceSnapshot,
    translatedText: "",
    errorMessage: "",
    isShowingTranslation: false,
    isTranslating: false,
  };
}

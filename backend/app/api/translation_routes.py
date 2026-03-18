from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_matcher_llm
from app.schemas import TranslationRequest, TranslationResponse
from app.services.llm_client import OpenAICompatibleMatcherLLM


router = APIRouter(prefix="/translate", tags=["translate"])


@router.post("/chinese", response_model=TranslationResponse)
async def translate_to_chinese(
    request: TranslationRequest,
    llm: OpenAICompatibleMatcherLLM = Depends(get_matcher_llm),
) -> TranslationResponse:
    try:
        translation = await llm.translate_to_chinese(text=request.text)
    except ValueError as exc:
        if str(exc) == "Translation service is not configured.":
            raise HTTPException(status_code=503, detail="Translation service unavailable") from exc
        raise HTTPException(status_code=502, detail="Translation failed") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Translation failed") from exc

    return TranslationResponse(translation=translation)

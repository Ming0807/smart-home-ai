from fastapi import APIRouter, Depends, status

from server.models.chat import ChatRequest, ChatResponse
from server.services.intent_router import IntentRouter, get_intent_router
from server.services.llm_manager import LLMManager, get_llm_manager

router = APIRouter(tags=["chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
)
def chat(
    request: ChatRequest,
    intent_router: IntentRouter = Depends(get_intent_router),
    llm_manager: LLMManager = Depends(get_llm_manager),
) -> ChatResponse:
    intent_match = intent_router.classify(request.message)
    placeholder_response = intent_router.get_placeholder_response(intent_match.intent)
    if placeholder_response is not None:
        return ChatResponse(
            reply=placeholder_response.reply,
            intent=placeholder_response.intent,
            source="placeholder",
        )

    llm_response = llm_manager.generate_reply(request.message)
    return ChatResponse(
        reply=llm_response.reply,
        intent="general_chat",
        source=llm_response.source,
    )

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request, status


from backend.use_cases.use_case_2.models import FAQItem, FAQQueryRequest, FAQQueryResponse, FAQRawTextRequest
from backend.use_cases.use_case_2.service import FAQService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/faq", tags=["FAQ Chatbot"])


def get_faq_service(request: Request) -> FAQService:
    """Dependency injector: reads FAQService singleton from app.state (set at lifespan startup)."""
    return request.app.state.faq_service


@router.post("/chat", response_model=FAQQueryResponse, status_code=status.HTTP_200_OK)
async def chat_faq(
    request: FAQQueryRequest,
    service: FAQService = Depends(get_faq_service),
) -> FAQQueryResponse:
    """Process user query and return FAQ assistant answer with execution metrics."""
    return await service.process_query(request)


@router.post("/item", status_code=status.HTTP_201_CREATED)
async def add_faq_item(
    item: FAQItem,
    service: FAQService = Depends(get_faq_service),
) -> dict[str, Any]:
    """Add a new FAQ item and re-index vector database."""
    saved_items = service.add_faq_item(item)
    saved_id = saved_items[0].id if (isinstance(saved_items, list) and len(saved_items) > 0) else 0
    return {"status": "success", "message": f"FAQ item #{saved_id} added and indexed!", "id": saved_id}



@router.post("/bulk", status_code=status.HTTP_201_CREATED)
async def add_bulk_faq_items(
    items: list[FAQItem],
    service: FAQService = Depends(get_faq_service),
) -> dict[str, Any]:
    """Add multiple FAQ items (from JSON array) and re-index vector database."""
    total_count = service.bulk_add_faq_items(items)
    return {"status": "success", "message": f"Successfully added {len(items)} FAQ items. Total indexed: {total_count}"}


@router.post("/parse-text", status_code=status.HTTP_201_CREATED)
async def parse_and_add_text(
    request: FAQRawTextRequest,
    service: FAQService = Depends(get_faq_service),
) -> dict[str, Any]:
    """Parse unstructured text into structured Q&A items, save to dataset, and re-index."""
    extracted = await service.parse_and_add_raw_text(request.raw_text)
    return {
        "status": "success",
        "extracted_count": len(extracted),
        "message": f"Extracted and indexed {len(extracted)} FAQ items from raw text.",
        "items": [item.model_dump() for item in extracted],
    }



@router.post("/reload", status_code=status.HTTP_200_OK)
async def reload_faq_index(
    service: FAQService = Depends(get_faq_service),
) -> dict[str, Any]:
    """Force reload and re-indexing of FAQ dataset from JSON file."""
    count = service.ensure_index_loaded(force_reload=True)
    return {"status": "success", "message": f"Successfully re-indexed {count} FAQ items."}


@router.get("/history/{session_id}", status_code=status.HTTP_200_OK)
async def get_chat_history(
    session_id: str,
    service: FAQService = Depends(get_faq_service),
) -> dict[str, Any]:
    """Retrieve chat history for a session."""
    history = service.get_session_history(session_id)
    return {"session_id": session_id, "messages": history}


@router.delete("/history/{session_id}", status_code=status.HTTP_200_OK)
async def clear_chat_history(
    session_id: str,
    service: FAQService = Depends(get_faq_service),
) -> dict[str, Any]:
    """Clear chat history for a session."""
    service.clear_session_history(session_id)
    return {"status": "success", "message": f"Session history for '{session_id}' cleared."}


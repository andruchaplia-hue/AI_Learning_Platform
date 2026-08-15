import json
import logging
from typing import Any

from backend.use_cases.use_case_2.retriever import FAQRetriever
from backend.use_cases.use_case_2.models import RetrievedFAQ

logger = logging.getLogger(__name__)

from backend.infrastructure.llm.compat import kernel_function


class FAQPlugin:
    """Semantic Kernel Plugin exposing search_faq native tool calling."""

    def __init__(self, retriever: FAQRetriever, top_k: int = 3, threshold: float = 0.75):
        self.retriever = retriever
        self.top_k = top_k
        self.threshold = threshold

    @kernel_function(
        name="search_faq",
        description="Search the FAQ knowledge base for answers relevant to user queries."
    )
    def search_faq(self, query: str) -> str:
        """Search vector database for closest FAQ items matching user query."""
        logger.info(f"FAQPlugin: Executing vector search via FAQRetriever for query='{query}'")
        results = self.retriever.retrieve(query=query, top_k=self.top_k, min_score=0.0)


        if not results:
            return json.dumps({"status": "no_results", "message": "No FAQ entries found in knowledge base."})

        valid_matches = [r for r in results if r.score >= self.threshold]
        if not valid_matches:
            return json.dumps({
                "status": "low_confidence",
                "message": f"Closest match had similarity score below threshold ({results[0].score:.2f} < {self.threshold}).",
                "top_result": {
                    "id": results[0].id,
                    "question": results[0].question,
                    "score": results[0].score,
                }
            })

        payload = []
        for r in valid_matches:
            payload.append({
                "id": r.id,
                "category": r.category,
                "question": r.question,
                "answer": r.answer,
                "similarity_score": r.score,
            })

        return json.dumps({"status": "success", "results": payload}, ensure_ascii=False)

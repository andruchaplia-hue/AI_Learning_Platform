from pydantic import BaseModel


class FAQItem(BaseModel):
    """Domain model representing an FAQ entry."""
    id: int
    category: str
    question: str
    answer: str

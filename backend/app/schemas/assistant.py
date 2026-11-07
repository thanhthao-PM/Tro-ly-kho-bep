"""
Pydantic Schemas cho Module Assistant (Trợ lý AI Fact-based).
"""
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    role: str = Field(description="user | assistant")
    text: str


class AssistantMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    history: List[ChatTurn] = []


class VerifiedFact(BaseModel):
    id: str
    tool: str
    label: str
    value: str
    unit: Optional[str] = None
    as_of: str


class ProposedAction(BaseModel):
    type: str  # OPEN_EXPIRING_BATCH | OPEN_SHORTAGE | OPEN_REPLENISHMENT | OPEN_DISH
    target_id: Optional[UUID] = None
    label: str


class RecommendationItem(BaseModel):
    text: str
    assumptions: List[str] = []
    basis: str = "VERIFIED_FACT"


class AssistantMessageResponse(BaseModel):
    answer_text: str
    facts: List[VerifiedFact] = []
    recommendations: List[RecommendationItem] = []
    data_gaps: List[str] = []
    proposed_actions: List[ProposedAction] = []
    provider: str = "rule_based"
    request_id: str

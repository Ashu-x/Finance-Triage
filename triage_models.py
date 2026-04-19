"""
Pydantic models for triage report structure
"""

from pydantic import BaseModel, Field
from typing import List


class ClassificationResult(BaseModel):
    """Model for classification output from LLM"""
    urgency: str = Field(description="CRITICAL | HIGH | MEDIUM | LOW")
    intent: str = Field(description="Type of support request")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")


class ExtractedEntities(BaseModel):
    """Model for extracted financial entities"""
    transaction_ids: List[str] = Field(default_factory=list)
    amounts: List[str] = Field(default_factory=list)
    dates: List[str] = Field(default_factory=list)
    account_numbers: List[str] = Field(default_factory=list)


class TriageReport(BaseModel):
    """Final triage report combining all analysis"""
    original_message: str
    classification: ClassificationResult
    extracted_entities: ExtractedEntities
    draft_response: str
    processing_time_ms: float

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class Trigger(BaseModel):
    trigger_type: Literal["news", "price", "filing", "insider", "theme"]
    headline: str
    theme_hint: str
    subthemes: List[str] = Field(default_factory=list)
    urgency: str = "medium"
    freshness: str = "new"
    confidence: float = 5.0


class Opportunity(BaseModel):
    ticker: str
    company_name: str
    theme: str
    subtheme: Optional[str] = None
    role: str
    positioning: str
    conviction_score: float
    priority_level: str
    horizon: str
    thesis: str
    why_now: str
    why_this_name: str
    ai_verdict: str


class ScanResult(BaseModel):
    run_type: str
    triggers: List[Trigger]
    opportunities: List[Opportunity]
    summary: str
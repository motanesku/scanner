from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


class Trigger(BaseModel):
    trigger_type: Literal["news", "price", "filing", "insider", "theme", "earnings", "market"]
    headline: str
    theme_hint: str
    subthemes: List[str] = Field(default_factory=list)
    urgency: str = "medium"
    freshness: str = "new"
    confidence: float = 5.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Opportunity(BaseModel):
    ticker: str
    company_name: str
    theme: str
    subtheme: Optional[str] = None
    role: str
    positioning: str
    market_cap_bucket: str = "Unknown"
    conviction_score: float
    priority_level: str
    horizon: str
    thesis: str
    why_now: str
    why_this_name: str
    ai_verdict: str
    status: str = "ACTIVE WATCH"

    trigger_stack: List[str] = Field(default_factory=list)
    trigger_count: int = 0
    market_confirmation: List[str] = Field(default_factory=list)
    next_confirmations: List[str] = Field(default_factory=list)
    failure_modes: List[str] = Field(default_factory=list)


class ThemeCard(BaseModel):
    theme_key: str
    theme_name: str
    subthemes: List[str] = Field(default_factory=list)
    theme_strength: float
    narrative_strength: float
    market_confirmation: str
    priority_level: str
    status: str
    why_now: str
    ai_verdict: str
    top_beneficiaries: List[str] = Field(default_factory=list)


class DailyReport(BaseModel):
    report_date: str
    top_themes: List[str] = Field(default_factory=list)
    top_tickers: List[str] = Field(default_factory=list)
    laggards: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)
    market_take: str
    actionable_focus: List[str] = Field(default_factory=list)


class ScanResult(BaseModel):
    run_type: str
    triggers: List[Trigger]
    opportunities: List[Opportunity]
    themes: List[ThemeCard]
    daily_report: DailyReport
    summary: str
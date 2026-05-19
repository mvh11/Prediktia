from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

RiskLevel = Literal["low", "medium", "high", "extreme"]


class AccaPickOut(BaseModel):
    fixture_id: int
    liga: str
    equipo_local: str
    equipo_visitante: str
    fecha: str = ""
    kickoff_in_minutes: int | None = Field(default=None)
    mercado: str
    pick: str
    cuota: float
    probabilidad: float
    ev: float
    ev_pct: float
    edge_pct: float
    confidence_pct: float
    implied_probability: float
    odds_source: Literal["bookmaker", "synthetic"]


class AccaProfileOut(BaseModel):
    min_picks: int
    max_picks: int
    target_odds_range: str


class AccaMetaOut(BaseModel):
    candidates_pool_size: int = 0
    eligible_after_filters: int = 0
    bookmaker_odds_picks: int = 0
    independence_assumption: str = ""
    fetch_odds: bool = True
    fixtures_upstream_total: int = 0
    fixtures_after_schedule_filter: int = 0
    fixtures_after_schedule_strict: int = 0
    schedule_filter_fallback: bool = False
    schedule_discard_reasons: dict[str, int] = Field(default_factory=dict)
    fixtures_source: str = "api_football"
    requested_date: str = ""
    resolved_date: str = ""
    auto_shifted_date: bool = False
    unique_fixtures_count: int = 0
    risk_profile_validation: dict[str, Any] = Field(default_factory=dict)
    persist_status: str = "not_attempted"
    persist_error: str | None = None
    persist_verify_message: str | None = None
    upstream_warning: str | None = None
    cache_stale: bool = False


class SmartAccaResponse(BaseModel):
    date: str
    model_version: str
    risk: RiskLevel
    risk_label: str
    profile: AccaProfileOut
    picks: list[AccaPickOut]
    pick_count: int
    total_odds: float
    combined_probability: float
    combined_ev: float
    combined_ev_pct: float
    confidence_score: float = Field(..., description="0–100")
    risk_score: float = Field(..., description="0–100")
    volatility_score: float = Field(..., description="0–100")
    meta: AccaMetaOut
    message: str | None = None
    acca_id: str | None = None


class AccaHistoryItemOut(BaseModel):
    id: str = Field(description="UUID de la combinada (alias de acca_id).")
    acca_id: str
    created_at: str
    risk: str
    risk_label: str = ""
    total_odds: float
    total_ev: float = Field(description="EV combinado en % (mismo valor que combined_ev_pct).")
    combined_ev_pct: float = 0.0
    confidence: float = Field(description="Confianza agregada 0–100.")
    confidence_score: float = 0.0
    picks_count: int = 0
    pick_count: int = 0
    status: Literal["pending"] = "pending"
    date: str = ""
    model_version: str = ""

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: object) -> str:
        return "pending"


class AccaHistoryListResponse(BaseModel):
    items: list[AccaHistoryItemOut]
    database_configured: bool = False
    database_message: str | None = None

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

RiskLevel = Literal["low", "medium", "high", "extreme"]


class AccaPickOut(BaseModel):
    fixture_id: int
    liga: str
    equipo_local: str
    equipo_visitante: str
    fecha: str = ""
    kickoff_in_minutes: int | None = Field(
        default=None,
        description="Minutos hasta el inicio (UTC) al generar la ACCA; None si no se pudo calcular.",
    )
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
    candidates_pool_size: int
    eligible_after_filters: int
    bookmaker_odds_picks: int
    independence_assumption: str
    fetch_odds: bool
    fixtures_upstream_total: int = 0
    fixtures_after_schedule_filter: int = 0
    fixtures_after_schedule_strict: int = 0
    schedule_filter_fallback: bool = False
    schedule_discard_reasons: dict[str, int] = Field(default_factory=dict)
    fixtures_source: str = Field(
        default="api_football",
        description="Origen de la lista de fixtures para ACCA (siempre API-Football + caché en memoria; no PostgreSQL).",
    )
    requested_date: str = Field(
        ...,
        description="Día UTC de referencia (query ?date= o hoy UTC si se omite).",
    )
    resolved_date: str = Field(
        ...,
        description="Día UTC efectivo usado para fixtures y picks (puede avanzar si hoy no hay pre-partido).",
    )
    auto_shifted_date: bool = Field(
        ...,
        description="True si no se envió ?date= y se eligió un día posterior con fixtures pre-partido válidos.",
    )
    unique_fixtures_count: int = Field(
        default=0,
        ge=0,
        description="Cantidad de fixture_id distintos en la combinada; debe coincidir con pick_count.",
    )
    average_pick_probability: float = Field(
        default=0.0,
        description="Media de probabilidades modelo por pick seleccionado.",
    )
    average_pick_odds: float = Field(
        default=0.0,
        description="Media de cuotas por pick.",
    )
    highest_pick_odds: float = Field(
        default=0.0,
        description="Cuota máxima entre picks de la combinada.",
    )
    risk_profile_validation: dict[str, Any] = Field(
        default_factory=dict,
        description="Checks de unicidad de fixture, suelo de P(combinada), picks excepcionales, etc.",
    )
    persist_status: str = Field(
        default="not_attempted",
        description="skipped | ok | failed — resultado de persistencia PostgreSQL.",
    )
    persist_error: str | None = Field(
        default=None,
        description="Mensaje si persist_status=failed (no silenciar errores).",
    )
    persist_verify_message: str | None = Field(
        default=None,
        description="Advertencia si el insert fue ok pero la verificación post-commit falló.",
    )


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
    confidence_score: float = Field(..., description="0–100, mayor = más confianza agregada.")
    risk_score: float = Field(..., description="0–100, mayor = más riesgo.")
    volatility_score: float = Field(..., description="0–100, mayor = más volatilidad.")
    meta: AccaMetaOut
    message: str | None = None
    acca_id: str | None = Field(
        default=None,
        description="UUID persistido en PostgreSQL cuando DATABASE_URL está configurado.",
    )


AccaSettlementStatus = Literal["pending", "won", "lost"]


class AccaHistoryItemOut(BaseModel):
    acca_id: str
    date: str
    risk: str
    risk_label: str
    total_odds: float
    combined_ev_pct: float
    confidence_score: float
    pick_count: int
    created_at: str
    status: AccaSettlementStatus = Field(
        default="pending",
        description="Liquidación agregada de la combinada: pending | won | lost.",
    )
    result: str | None = Field(
        default=None,
        description="Campo legacy; preferir `status`.",
    )
    roi: float | None = None
    settled_at: str | None = Field(
        default=None,
        description="Marca temporal UTC de liquidación automática o manual (won/lost).",
    )
    model_version: str

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: object) -> str:
        if isinstance(v, str) and v.lower() in ("pending", "won", "lost"):
            return v.lower()
        return "pending"


class AccaSettleRequest(BaseModel):
    status: AccaSettlementStatus
    roi: float | None = Field(
        default=None,
        description="ROI decimal (ej. 0.42 = +42% sobre unidad de stake); opcional.",
    )


class AccaHistoryListResponse(BaseModel):
    items: list[AccaHistoryItemOut]
    database_configured: bool = False

from typing import Literal

from pydantic import BaseModel, Field

ValueGrade = Literal["risky", "good", "high", "elite"]


class ValueBetPick(BaseModel):
    """Un pick con EV positivo (probabilidad y cuota mock por ahora)."""

    fixture_id: int
    league_id: int = Field(0, description="ID de competición API-Football (0 si no viene).")
    country: str = Field("", description="País de la competición según upstream.")
    league_name: str = Field("", description="Nombre corto de la competición (sin país), tal cual API.")
    team_home_id: int = Field(0, description="ID equipo local API-Football (logo media.api-sports.io).")
    team_away_id: int = Field(0, description="ID equipo visitante API-Football.")
    equipo_local: str
    equipo_visitante: str
    liga: str = Field(..., description="Texto de competición para UI, p. ej. 'Premier League (England)'.")
    fecha: str = Field(..., description="ISO8601 del fixture.")
    estado_partido: str
    mercado: str
    pick: str
    cuota: float = Field(..., ge=1.01, description="Cuota decimal europea.")
    probabilidad: float = Field(..., ge=0.0, le=1.0, description="Probabilidad estimada [0,1].")
    ev: float = Field(..., gt=0.0, description="EV = probabilidad * cuota - 1.")
    value_grade: ValueGrade = Field(
        ...,
        description="Clase visual por EV: risky, good, high, elite.",
    )


class ValueBetsResponse(BaseModel):
    """Respuesta de /value-bets: mismos fixtures que /matches, picks derivados en backend."""

    date: str
    source: str = Field(default="mock-ev", description="Origen del cálculo (mock hasta modelo real).")
    picks_count: int
    picks: list[ValueBetPick]
    upstream_warning: str | None = None
    cache_stale: bool = False
    plan_tier: str = "free"
    plan_limited: bool = False
    picks_limit: int | None = None

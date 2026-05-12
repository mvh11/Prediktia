from typing import Any

from pydantic import BaseModel, Field


class MatchesResponse(BaseModel):
    """Respuesta del endpoint /matches: metadatos + lista tal como la devuelve la API."""

    date: str = Field(..., description="Fecha consultada (YYYY-MM-DD).")
    source: str = Field(default="api-football", description="Origen de los datos.")
    results_count: int = Field(..., description="Número de partidos devueltos.")
    raw_fixtures: list[dict[str, Any]] = Field(
        ...,
        description="Lista de partidos en el formato de API-Football (array `response`).",
    )

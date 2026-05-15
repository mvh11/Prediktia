from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import acca, matches, value_bets

app = FastAPI(
    title="Prediktia API",
    description="Backend MVP: partidos vía API-Football y base para ACCA.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(matches.router)
app.include_router(value_bets.router)
app.include_router(acca.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Comprueba que el servidor responde (útil para pruebas rápidas)."""
    return {"status": "ok"}

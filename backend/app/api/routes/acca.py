from fastapi import APIRouter

router = APIRouter(prefix="/acca", tags=["acca"])


@router.get("")
def acca_placeholder() -> dict:
    """
    Reservado para combinar probabilidades Poisson y generar ACCA por riesgo.

    En el MVP actual solo devuelve un mensaje; la lógica se añadirá después.
    """
    return {
        "status": "not_implemented",
        "message": "El generador de combinadas ACCA se implementará en una fase posterior.",
    }

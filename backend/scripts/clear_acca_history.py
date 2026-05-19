"""
Vacía la tabla acca_history (demo / reinicio de historial).

Uso (desde backend/):
  python -m scripts.clear_acca_history

Requiere DATABASE_URL en el entorno o en backend/.env (Neon / local).
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.config import get_settings
from app.db.migrations import truncate_acca_history


def main() -> int:
    get_settings.cache_clear()
    settings = get_settings()
    if not settings.database_url:
        print("DATABASE_URL no configurada.", file=sys.stderr)
        return 1

    ok, err = truncate_acca_history(settings.database_url)
    if ok:
        print("acca_history vaciada correctamente.")
        return 0
    print(f"Error: {err}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

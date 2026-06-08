"""
Generación mock de picks con EV positivo a partir de fixtures API-Football.

- 1X2, totales 2.5, BTTS y doble oportunidad usan probabilidades coherentes por partido
  (no tres 1X2 independientes que permitan EV alto en local y visita a la vez).
- Como mucho una línea EV+ por mercado mutuamente excluyente (p. ej. un solo 1X2 por fixture).
- EV objetivo acotado en ligas de bajo volumen / señales de reserva o femenino no élite.
"""

from __future__ import annotations

import hashlib
import struct
from typing import Any, Literal

from app.services.league_format import format_league_display
from app.services.league_priority import league_priority_score

# Convención API-Football: teams.home = local, teams.away = visitante.
# 1X2: "Victoria local" = home; "Victoria visitante" = away.
# Doble oportunidad: 1X = local o empate; X2 = empate o visitante (probs derivadas del mismo trío 1X2).
ValueGrade = Literal["risky", "good", "high", "elite"]


def _u01(seed: str) -> float:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return struct.unpack(">I", digest[:4])[0] / 2**32


def _read_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _format_liga_display(league_name: str, country: str) -> str:
    name = (league_name or "").strip() or "—"
    c = (country or "").strip()
    if not c:
        return name
    nl = name.lower()
    cl = c.lower()
    if cl in nl:
        return name
    return f"{name} ({country})"


def _build_estado_partido(fixture: dict[str, Any]) -> str:
    status = fixture.get("status") if isinstance(fixture.get("status"), dict) else {}
    long_s = _read_str(status.get("long")) if isinstance(status, dict) else None
    short_s = _read_str(status.get("short")) if isinstance(status, dict) else None
    elapsed = status.get("elapsed") if isinstance(status, dict) else None

    if long_s and short_s and long_s != short_s:
        return f"{short_s} — {long_s}"
    if long_s:
        return long_s
    if short_s:
        return short_s
    if isinstance(elapsed, (int, float)) and elapsed == elapsed:
        return f"En juego ({int(elapsed)}′)"
    return "Desconocido"


def _parse_fixture_row(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    fx = item.get("fixture")
    if not isinstance(fx, dict):
        return None
    fid = fx.get("id")
    if not isinstance(fid, int):
        return None
    fecha = _read_str(fx.get("date"))
    if not fecha:
        return None

    league = item.get("league") if isinstance(item.get("league"), dict) else {}
    teams = item.get("teams") if isinstance(item.get("teams"), dict) else {}
    home = teams.get("home") if isinstance(teams.get("home"), dict) else {}
    away = teams.get("away") if isinstance(teams.get("away"), dict) else {}

    league_name = _read_str(league.get("name")) or "—"
    country = _read_str(league.get("country")) or ""
    lid_raw = league.get("id")
    league_id = int(lid_raw) if isinstance(lid_raw, int) else 0

    hid = home.get("id")
    aid = away.get("id")
    team_home_id = int(hid) if isinstance(hid, int) else 0
    team_away_id = int(aid) if isinstance(aid, int) else 0

    return {
        "fixture_id": fid,
        "fecha": fecha,
        "league_id": league_id,
        "country": country,
        "league_name": league_name,
        "liga": _format_liga_display(league_name, country),
        "equipo_local": _read_str(home.get("name")) or "—",
        "equipo_visitante": _read_str(away.get("name")) or "—",
        "team_home_id": team_home_id,
        "team_away_id": team_away_id,
        "estado_partido": _build_estado_partido(fx),
    }


def _fixture_ev_cap(base: dict[str, Any]) -> float:
    """Techo duro de EV mock en competiciones de baja credibilidad / volumen."""
    s = f"{base.get('country', '')} {base.get('league_name', '')} {base.get('liga', '')}".lower()
    hard = (
        "women",
        "womens",
        "femenin",
        "femenina",
        "ladies",
        "girl",
        "u17",
        "u18",
        "u19",
        "u20",
        "u21",
        "u22",
        "u23",
        "sub-17",
        "sub-19",
        "sub-21",
        "sub 17",
        "sub 19",
        "sub 21",
        "juvenil",
        "youth",
        "academy",
        "reserva",
        "reserve",
        "b team",
        "regional",
        "amateur",
        "tercera",
        "segunda b",
        "liga iii",
        " iv",
        " iii",
        "district",
        "isle of man",
    )
    if any(x in s for x in hard):
        return 0.085
    if any(x in s for x in (" ii", " 2nd ", "second division", "segunda division")):
        return 0.112
    return 0.198


# Big 5 + copas UEFA (EV más conservador en mercados “seguros”).
TOP_EU_LIQUID_IDS: frozenset[int] = frozenset({39, 140, 135, 78, 61, 2, 3, 848})

# LATAM + copas (Prediktia); IDs API-Football habituales — ajustar en dashboard si difieren.
LATAM_EDITORIAL_IDS: frozenset[int] = frozenset(
    {
        265,  # Chile Primera
        128,  # Argentina LPF
        71,
        72,  # Brasil Serie A / B
        262,  # México Liga MX
        239,  # Colombia Primera A
        281,  # Perú Liga 1
        242,  # Ecuador LigaPro
        268,  # Uruguay Primera
        252,  # Paraguay Primera
        13,  # Libertadores
        11,  # Sudamericana (id frecuente en API-Football v3)
    }
)


def _latam_string_context(base: dict[str, Any]) -> bool:
    s = f"{base.get('country', '')} {base.get('league_name', '')} {base.get('liga', '')}".lower()
    if "libertadores" in s or "sudamericana" in s:
        return True
    hints = (
        ("mexico", "liga mx"),
        ("méxico", "liga mx"),
        ("chile", "primera"),
        ("argentina", "liga"),
        ("argentina", "lpf"),
        ("argentina", "primera"),
        ("brazil", "brasileir"),
        ("brasil", "brasileir"),
        ("colombia", "primera"),
        ("colombia", "betplay"),
        ("peru", "liga 1"),
        ("perú", "liga 1"),
        ("ecuador", "liga pro"),
        ("uruguay", "primera"),
        ("paraguay", "primera"),
    )
    return any(c in s and k in s for c, k in hints)


def _dynamic_ev_cap(mercado: str, pick: str, prob: float, base: dict[str, Any], base_cap: float) -> float:
    """
    Caps dinámicos: doble oportunidad y favoritos con cuotas bajas no llevan EV extremo;
    ligas top más conservadoras; underdogs (prob baja / fair alto) pueden subir algo más.
    """
    fair = 1.0 / max(prob, 1e-6)
    lid = int(base.get("league_id") or 0)
    top_eu = lid in TOP_EU_LIQUID_IDS
    latam = lid in LATAM_EDITORIAL_IDS or _latam_string_context(base)
    major = top_eu or latam

    underdog = fair >= 3.55
    strong_fav = fair < 1.34
    fav_band = 1.30 <= fair <= 1.72

    cap = base_cap

    if mercado == "Doble oportunidad":
        cap = min(cap, 0.058 if top_eu else 0.072 if major else 0.084)
        if fair <= 1.85:
            cap = min(cap, 0.052 if top_eu else 0.062 if major else 0.074)
        return max(0.018, cap)

    if mercado == "1X2":
        if strong_fav:
            cap = min(cap, 0.065 if top_eu else 0.076)
        elif fav_band:
            cap = min(cap, 0.078 if top_eu else 0.088 if major else 0.098)
        elif fair <= 2.45:
            cap = min(cap, 0.092 if top_eu else 0.102 if major else 0.118)
        else:
            cap = min(cap, 0.118 if major else base_cap)
        if major and not underdog:
            cap = min(cap, 0.098 if top_eu else 0.112)
        if underdog:
            cap = min(base_cap, max(cap, 0.125))
        return max(0.018, cap)

    if mercado in ("Total goles", "Ambos marcan"):
        if fair <= 2.18:
            cap = min(cap, 0.082 if top_eu else 0.092 if major else 0.105)
        elif fair <= 2.55:
            cap = min(cap, 0.095 if major else 0.115)
        if underdog:
            cap = min(base_cap, max(cap, 0.128))
        return max(0.018, cap)

    return max(0.018, cap)


def _mock_target_ev(seed: str) -> float:
    """
    EV objetivo con distribución orgánica (determinista por semilla):

    * ~73% en +2%–+10% (mayoría).
    * ~21% en +10%–+18%.
    * ~6% en +18%–+20.5% (cola corta; raro en ligas con cap bajo).
    """
    u_band = _u01(seed + ":band")

    if u_band < 0.73:
        u1, u2 = _u01(seed + ":e1"), _u01(seed + ":e2")
        span = (u1 + u2) / 2.0
        span = span**1.08
        base_lo, base_hi = 0.02, 0.10
        ev_core = base_lo + span * (base_hi - base_lo)
    elif u_band < 0.94:
        u = _u01(seed + ":e3")
        ev_core = 0.10 + (u**0.92) * 0.08
    else:
        u = _u01(seed + ":e4")
        ev_core = 0.178 + u * 0.027

    jitter = (_u01(seed + ":jz") - 0.5) * 0.007
    ev_t = float(ev_core + jitter)
    ev_t = max(0.008, min(0.22, ev_t))
    return ev_t


def _coherent_quote(probabilidad: float, ev_target: float) -> tuple[float, float] | None:
    """Cuota decimal coherente con (p, EV): O = (1+EV)/p."""
    if probabilidad <= 0 or probabilidad >= 1:
        return None
    raw = (1.0 + ev_target) / probabilidad
    if not (1.08 <= raw <= 12.0):
        return None

    cuota = round(raw, 2)
    ev = round(probabilidad * cuota - 1.0, 4)

    if ev < 0.008:
        for _ in range(16):
            cuota = round(cuota + 0.01, 2)
            if cuota > 15.0:
                return None
            ev = round(probabilidad * cuota - 1.0, 4)
            if ev >= 0.008:
                break
        else:
            return None

    if ev > 0.24:
        for _ in range(20):
            cuota = round(cuota - 0.01, 2)
            if cuota < 1.05:
                return None
            ev = round(probabilidad * cuota - 1.0, 4)
            if ev <= 0.22:
                break

    if ev < 0.008 or ev > 0.24:
        return None
    return cuota, ev


def _assign_value_grade(ev: float) -> ValueGrade:
    if ev >= 0.172:
        return "elite"
    if ev >= 0.108:
        return "high"
    if ev >= 0.052:
        return "good"
    return "risky"


def _tripartite_probs(seed: str) -> tuple[float, float, float]:
    """Probabilidades 1X2 (local, empate, visita) que suman 1."""
    a = 0.06 + _u01(seed + ":a")
    b = 0.06 + _u01(seed + ":b")
    c = 0.06 + _u01(seed + ":c")
    s = a + b + c
    ph, pd, pa = a / s, b / s, c / s
    ph, pd, pa = round(ph, 4), round(pd, 4), round(pa, 4)
    s2 = ph + pd + pa
    return ph / s2, pd / s2, pa / s2


def _try_quote_with_ev_ladder(prob: float, seed: str, cap: float) -> tuple[float, float] | None:
    """Intenta varios EV objetivos (de mayor a menor) hasta obtener cuota válida."""
    ev0 = min(_mock_target_ev(seed + ":tgt"), cap)
    for scale in (1.0, 0.82, 0.64, 0.48, 0.035):
        ev_t = max(0.008, min(cap, ev0 * scale))
        cq = _coherent_quote(prob, ev_t)
        if cq:
            return cq
    return None


def _pick_row(
    base: dict[str, Any],
    mercado: str,
    pick: str,
    prob: float,
    seed: str,
    cap: float,
) -> dict[str, Any] | None:
    cap_eff = _dynamic_ev_cap(mercado, pick, prob, base, cap)
    cq = _try_quote_with_ev_ladder(prob, seed, cap_eff)
    if not cq:
        return None
    cuota, ev_r = cq
    return {
        "fixture_id": base["fixture_id"],
        "league_id": base["league_id"],
        "country": base["country"],
        "league_name": base["league_name"],
        "equipo_local": base["equipo_local"],
        "equipo_visitante": base["equipo_visitante"],
        "team_home_id": int(base.get("team_home_id") or 0),
        "team_away_id": int(base.get("team_away_id") or 0),
        "liga": base["liga"],
        "fecha": base["fecha"],
        "estado_partido": base["estado_partido"],
        "mercado": mercado,
        "pick": pick,
        "cuota": cuota,
        "probabilidad": prob,
        "ev": ev_r,
        "value_grade": _assign_value_grade(ev_r),
    }


def _best_exclusive_among_arms(
    base: dict[str, Any],
    fid: int,
    mercado: str,
    arms: list[tuple[str, float]],
    cap: float,
) -> dict[str, Any] | None:
    """
    Genera candidatos (pick, prob) del mismo mercado excluyente y conserva solo
    la línea con mayor EV realizado (como mucho una por fixture).
    """
    best: dict[str, Any] | None = None
    best_ev = -1.0
    for pick_label, prob in arms:
        seed = f"prediktia:value:{fid}:{mercado}:{pick_label}"
        row = _pick_row(base, mercado, pick_label, prob, seed, cap)
        if row and row["ev"] > best_ev:
            best_ev = row["ev"]
            best = row
    return best


def _fixture_priority(item: dict[str, Any]) -> float:
    league = item.get("league") if isinstance(item.get("league"), dict) else {}
    lid = int(league.get("id")) if isinstance(league.get("id"), int) else 0
    name = (league.get("name") or "") if isinstance(league.get("name"), str) else ""
    country = (league.get("country") or "") if isinstance(league.get("country"), str) else ""
    return league_priority_score(lid, name, country)


def build_mock_positive_ev_picks(fixtures: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    items = [x for x in fixtures if isinstance(x, dict)]
    items.sort(key=_fixture_priority, reverse=True)

    for item in items:
        base = _parse_fixture_row(item)
        if not base:
            continue
        fid = base["fixture_id"]
        cap = _fixture_ev_cap(base)
        seed_mx = f"prediktia:mx:{fid}"

        ph, pd, pa = _tripartite_probs(seed_mx + ":1x2")

        row_1x2 = _best_exclusive_among_arms(
            base,
            fid,
            "1X2",
            [
                ("Victoria local", ph),
                ("Empate", pd),
                ("Victoria visitante", pa),
            ],
            cap,
        )
        if row_1x2:
            out.append(row_1x2)

        p_1x = ph + pd
        p_x2 = pd + pa
        if p_1x > 0.999:
            p_1x = 0.999
        if p_x2 > 0.999:
            p_x2 = 0.999
        row_dc = _best_exclusive_among_arms(
            base,
            fid,
            "Doble oportunidad",
            [("1X", p_1x), ("X2", p_x2)],
            cap,
        )
        if row_dc:
            out.append(row_dc)

        p_over = round(0.34 + _u01(seed_mx + ":ou") * 0.32, 4)
        p_under = round(1.0 - p_over, 4)
        row_ou = _best_exclusive_among_arms(
            base,
            fid,
            "Total goles",
            [("Más de 2.5", p_over), ("Menos de 2.5", p_under)],
            cap,
        )
        if row_ou:
            out.append(row_ou)

        p_yes = round(0.28 + _u01(seed_mx + ":btts") * 0.44, 4)
        p_no = round(1.0 - p_yes, 4)
        row_btts = _best_exclusive_among_arms(
            base,
            fid,
            "Ambos marcan",
            [("Sí", p_yes), ("No", p_no)],
            cap,
        )
        if row_btts:
            out.append(row_btts)

    out.sort(key=lambda r: r["ev"], reverse=True)
    return out


_GRADE_RANK: dict[str, int] = {"elite": 0, "high": 1, "good": 2, "risky": 3}


def sort_picks_for_free_tier[T](picks: list[T]) -> list[T]:
    """
    Free: prioriza calidad (elite/high/good) sobre risky, luego EV y confianza.
    """

    def sort_key(p: T) -> tuple[int, float, float]:
        if isinstance(p, dict):
            grade = p.get("value_grade", "risky")
            ev = float(p.get("ev", 0))
            prob = float(p.get("probabilidad", 0))
        else:
            grade = getattr(p, "value_grade", "risky")
            ev = float(getattr(p, "ev", 0))
            prob = float(getattr(p, "probabilidad", 0))
        return (_GRADE_RANK.get(str(grade), 9), -ev, -prob)

    return sorted(picks, key=sort_key)

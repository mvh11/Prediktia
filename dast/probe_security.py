"""Probes de seguridad DAST (sin modificar la aplicación)."""
from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from typing import Any

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
TIMEOUT = 30.0


@dataclass
class ProbeResult:
    name: str
    status: str  # pass | warn | fail | info
    detail: str
    evidence: dict[str, Any] = field(default_factory=dict)


def main() -> None:
    results: list[ProbeResult] = []
    client = httpx.Client(base_url=BASE, timeout=TIMEOUT, follow_redirects=False)

    # --- Endpoints inventory ---
    endpoints = [
        ("GET", "/health"),
        ("GET", "/health/db"),
        ("GET", "/openapi.json"),
        ("GET", "/docs"),
        ("GET", "/matches"),
        ("GET", "/value-bets"),
        ("GET", "/acca"),
        ("GET", "/acca/history"),
        ("GET", "/debug/latam"),
        ("GET", "/debug/acca-filter"),
        ("GET", "/debug/acca-db-last"),
        ("GET", "/auth/me"),
        ("GET", "/payments/history"),
        ("POST", "/auth/login"),
        ("POST", "/auth/register"),
    ]
    inventory: dict[str, Any] = {}
    for method, path in endpoints:
        try:
            if method == "GET":
                r = client.get(path)
            else:
                r = client.post(path, json={})
            inventory[f"{method} {path}"] = {
                "status_code": r.status_code,
                "content_type": r.headers.get("content-type"),
            }
        except Exception as exc:
            inventory[f"{method} {path}"] = {"error": str(exc)}
    results.append(
        ProbeResult(
            name="endpoint_inventory",
            status="info",
            detail=f"Inventario de {len(endpoints)} rutas probadas contra {BASE}",
            evidence=inventory,
        )
    )

    # --- Security headers ---
    r = client.get("/health")
    headers = {k.lower(): v for k, v in r.headers.items()}
    security_headers = [
        "strict-transport-security",
        "content-security-policy",
        "x-content-type-options",
        "x-frame-options",
        "referrer-policy",
        "permissions-policy",
        "x-xss-protection",
    ]
    missing = [h for h in security_headers if h not in headers]
    results.append(
        ProbeResult(
            name="security_headers",
            status="warn" if missing else "pass",
            detail=f"Cabeceras de seguridad ausentes: {', '.join(missing) or 'ninguna (todas presentes)'}",
            evidence={"response_headers": dict(r.headers), "missing": missing},
        )
    )

    # --- CORS ---
    cors = client.options(
        "/health",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    acao = cors.headers.get("access-control-allow-origin")
    results.append(
        ProbeResult(
            name="cors",
            status="warn" if acao == "*" else ("pass" if acao is None else "info"),
            detail=f"Access-Control-Allow-Origin: {acao!r}",
            evidence={
                "status_code": cors.status_code,
                "access-control-allow-origin": acao,
                "access-control-allow-methods": cors.headers.get("access-control-allow-methods"),
                "access-control-allow-headers": cors.headers.get("access-control-allow-headers"),
            },
        )
    )

    # --- Auth: protected routes without token ---
    for path in ("/auth/me", "/payments/history"):
        r = client.get(path)
        results.append(
            ProbeResult(
                name=f"auth_required_{path}",
                status="pass" if r.status_code == 401 else "fail",
                detail=f"{path} sin token -> HTTP {r.status_code}",
                evidence={"body": r.text[:500]},
            )
        )

    # --- Auth: invalid token ---
    r = client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    results.append(
        ProbeResult(
            name="auth_invalid_token",
            status="pass" if r.status_code == 401 else "fail",
            detail=f"Token invalido -> HTTP {r.status_code}",
            evidence={"body": r.text[:500]},
        )
    )

    # --- Parameter validation ---
    r = client.get("/matches", params={"date": "' OR 1=1--"})
    results.append(
        ProbeResult(
            name="param_validation_date",
            status="pass" if r.status_code == 400 else "warn",
            detail=f"/matches?date=SQLi-like -> HTTP {r.status_code}",
            evidence={"body": r.text[:500]},
        )
    )
    r = client.get("/acca", params={"risk": "invalid_risk"})
    results.append(
        ProbeResult(
            name="param_validation_risk",
            status="pass" if r.status_code == 422 else "warn",
            detail=f"/acca?risk=invalid -> HTTP {r.status_code}",
            evidence={"body": r.text[:500]},
        )
    )

    # --- Error exposure ---
    r = client.get("/nonexistent-route-xyz")
    body = r.text
    leak_terms = ["traceback", "sqlalchemy", "psycopg", "jwt_secret", "api_football"]
    found = [t for t in leak_terms if t.lower() in body.lower()]
    results.append(
        ProbeResult(
            name="error_exposure_404",
            status="pass" if not found else "fail",
            detail=f"404 sin fugas sensibles; términos detectados: {found or 'ninguno'}",
            evidence={"status_code": r.status_code, "body_snippet": body[:500]},
        )
    )

    # --- Sensitive info in openapi ---
    r = client.get("/openapi.json")
    openapi_text = r.text.lower()
    sensitive_in_schema = [
        t
        for t in ("jwt_secret", "webpay_api_key", "database_url", "api_football_key")
        if t in openapi_text
    ]
    results.append(
        ProbeResult(
            name="openapi_sensitive_fields",
            status="pass" if not sensitive_in_schema else "fail",
            detail=f"OpenAPI expone campos sensibles: {sensitive_in_schema or 'no'}",
            evidence={"paths_count": len(r.json().get("paths", {})) if r.status_code == 200 else 0},
        )
    )

    # --- Debug endpoints unauthenticated ---
    for path in ("/debug/latam", "/debug/acca-db-last", "/debug/acca-filter"):
        r = client.get(path)
        results.append(
            ProbeResult(
                name=f"debug_exposure_{path}",
                status="warn" if r.status_code == 200 else "info",
                detail=f"{path} sin auth -> HTTP {r.status_code}",
                evidence={"body_snippet": r.text[:300]},
            )
        )

    # --- Health/db info disclosure ---
    r = client.get("/health/db")
    db_body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    sensitive_keys = [k for k in db_body if "password" in k.lower() or "secret" in k.lower()]
    results.append(
        ProbeResult(
            name="health_db_disclosure",
            status="warn" if "database_url_preview" in db_body or sensitive_keys else "pass",
            detail=f"/health/db keys: {list(db_body.keys())}",
            evidence={"body": db_body},
        )
    )

    print(json.dumps({"target": BASE, "results": [asdict(x) for x in results]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

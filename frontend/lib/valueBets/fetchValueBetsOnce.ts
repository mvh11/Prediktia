import { API_URL } from "@/lib/api";
import { authHeaders } from "@/lib/auth/headers";
import type { UserTier } from "@/lib/auth/types";
import { canUseFullValueBets, FREE_VALUE_PICKS_LIMIT, normalizeTier } from "@/lib/plans";

import type { ValueBetPick, ValueBetsResponse } from "./types";

const cacheByKey = new Map<string, ValueBetsResponse>();
const inflightByKey = new Map<string, Promise<ValueBetsResponse>>();

function buildCacheKey(accessToken?: string | null, authTier?: UserTier | null): string {
  return `${accessToken ?? ""}::${authTier ?? "anon"}`;
}

/** Invalida caché (p. ej. al login/logout o cambio de plan). */
export function clearValueBetsCache(): void {
  cacheByKey.clear();
  inflightByKey.clear();
}

function applyClientPlanLimit(data: ValueBetsResponse, authTier?: UserTier | null): ValueBetsResponse {
  const tier = authTier ?? normalizeTier(data.plan_tier);
  if (canUseFullValueBets(tier)) {
    if (data.plan_limited) {
      console.warn(
        "[value-bets] Usuario con tier de pago pero backend respondió plan_limited=true; " +
          "mostrando picks recibidos (verificar Authorization Bearer).",
      );
    }
    return {
      ...data,
      plan_tier: tier,
      plan_limited: false,
      picks_limit: null,
    };
  }

  const limit = data.picks_limit ?? FREE_VALUE_PICKS_LIMIT;
  const picks = Array.isArray(data.picks) ? data.picks : [];
  const sliced = picks.slice(0, limit);
  return {
    ...data,
    picks: sliced,
    picks_count: sliced.length,
    plan_tier: tier,
    plan_limited: true,
    picks_limit: limit,
  };
}

/**
 * Una petición a `/value-bets` por token+tier: reutiliza caché o promesa en curso por clave.
 */
export function fetchValueBetsOnce(
  accessToken?: string | null,
  authTier?: UserTier | null,
): Promise<ValueBetsResponse> {
  const key = buildCacheKey(accessToken, authTier);

  const cached = cacheByKey.get(key);
  if (cached) {
    return Promise.resolve(cached);
  }

  const pending = inflightByKey.get(key);
  if (pending) {
    return pending;
  }

  const promise = (async () => {
    const res = await fetch(`${API_URL}/value-bets`, {
      cache: "no-store",
      headers: authHeaders(undefined, accessToken),
    });
    if (!res.ok) {
      console.warn(`[value-bets] HTTP ${res.status} — respuesta vacía para no romper la demo`);
      const empty: ValueBetsResponse = {
        date: "",
        picks_count: 0,
        picks: [],
        upstream_warning: "Backend no disponible temporalmente.",
        cache_stale: false,
        plan_tier: authTier ?? "free",
        plan_limited: !canUseFullValueBets(normalizeTier(authTier)),
        picks_limit: canUseFullValueBets(normalizeTier(authTier)) ? null : FREE_VALUE_PICKS_LIMIT,
      };
      cacheByKey.set(key, empty);
      return empty;
    }
    const data = applyClientPlanLimit((await res.json()) as ValueBetsResponse, authTier);
    if (!Array.isArray(data.picks)) {
      data.picks = [];
      data.picks_count = 0;
    }
    cacheByKey.set(key, data);
    return data;
  })();

  inflightByKey.set(key, promise);

  return promise.finally(() => {
    inflightByKey.delete(key);
  });
}

/** Aplica límite Free en UI (defensa extra si el payload viene sin recortar). */
export function limitValuePicksForPlan(
  picks: ValueBetPick[],
  options: {
    fullValue: boolean;
    picksLimit?: number | null;
    planLimited?: boolean;
  },
): ValueBetPick[] {
  if (options.fullValue) {
    return picks;
  }
  const limit = options.picksLimit ?? FREE_VALUE_PICKS_LIMIT;
  if (!options.planLimited && picks.length <= limit) {
    return picks;
  }
  return picks.slice(0, limit);
}

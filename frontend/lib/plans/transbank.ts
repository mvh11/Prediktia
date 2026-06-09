import { API_URL } from "@/lib/api";
import { authHeaders } from "@/lib/auth/headers";

export type WebpayCreateResponse = {
  url: string;
  token: string;
};

export type CheckoutResult =
  | { ok: true; url: string; token: string }
  | { ok: false; message: string };

export function isCheckoutFailure(
  result: CheckoutResult,
): result is { ok: false; message: string } {
  return result.ok === false;
}

function formatPaymentError(status: number, body: { detail?: string } | null): string {
  if (body?.detail && typeof body.detail === "string") {
    return body.detail;
  }
  if (status === 401) {
    return "Debes iniciar sesión para contratar Premium.";
  }
  if (status === 400) {
    return "No se puede procesar este pago con tu plan actual.";
  }
  if (status === 503) {
    return "Los pagos no están disponibles temporalmente. Intenta más tarde.";
  }
  if (status === 502) {
    return "Transbank no respondió correctamente. Intenta de nuevo en unos minutos.";
  }
  return "No se pudo iniciar el pago con Webpay.";
}

/** Redirige al formulario de pago de Transbank (POST con token_ws). */
export function redirectToWebpay(url: string, token: string): void {
  const form = document.createElement("form");
  form.method = "POST";
  form.action = url;
  form.style.display = "none";

  const input = document.createElement("input");
  input.type = "hidden";
  input.name = "token_ws";
  input.value = token;
  form.appendChild(input);

  document.body.appendChild(form);
  form.submit();
}

export async function startPremiumCheckout(accessToken: string): Promise<CheckoutResult> {
  const res = await fetch(`${API_URL}/payments/webpay/create`, {
    method: "POST",
    headers: {
      ...authHeaders({ "Content-Type": "application/json" }, accessToken),
    },
    body: JSON.stringify({ plan: "premium" }),
  });

  let body: { detail?: string } | WebpayCreateResponse | null = null;
  try {
    body = (await res.json()) as { detail?: string } | WebpayCreateResponse;
  } catch {
    body = null;
  }

  if (!res.ok) {
    const errBody = body && "detail" in body ? body : null;
    return { ok: false as const, message: formatPaymentError(res.status, errBody) };
  }

  const data = body as WebpayCreateResponse;
  if (!data?.url || !data?.token) {
    return { ok: false as const, message: "Respuesta inválida del servidor de pagos." };
  }

  return { ok: true as const, url: data.url, token: data.token };
}

export async function startVipContact(): Promise<CheckoutResult> {
  return {
    ok: false as const,
    message:
      "El upgrade a VIP es por contacto directo. Escríbenos desde la sección Legal o contacto.",
  };
}

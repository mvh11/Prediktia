/**
 * Stubs para futura integración Webpay Plus (Transbank).
 * NO contiene credenciales ni llamadas reales.
 */

export type CheckoutResult = {
  ok: false;
  message: string;
};

export async function startPremiumCheckout(): Promise<CheckoutResult> {
  return {
    ok: false,
    message:
      "Próximamente integración Transbank (Webpay Plus). Tu cuenta seguirá en Free hasta activar el pago.",
  };
}

export async function startVipContact(): Promise<CheckoutResult> {
  return {
    ok: false,
    message:
      "Próximamente podrás solicitar upgrade a VIP. Por ahora escríbenos desde la sección Legal o contacto.",
  };
}

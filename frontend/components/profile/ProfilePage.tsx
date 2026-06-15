"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { PageShell } from "@/components/layout/PageShell";
import {
  changePasswordRequest,
  fetchPaymentHistory,
  updateProfileRequest,
} from "@/lib/auth/api";
import type { PaymentHistoryItem } from "@/lib/auth/types";
import { isPaidTier, normalizeTier, tierLabel } from "@/lib/plans";

function tierBadgeClasses(tier: ReturnType<typeof normalizeTier>): string {
  switch (tier) {
    case "admin":
      return "bg-rose-500/20 text-rose-100 ring-rose-400/35";
    case "vip":
      return "bg-fuchsia-500/20 text-fuchsia-100 ring-fuchsia-400/35";
    case "premium":
      return "bg-cyan-500/20 text-cyan-100 ring-cyan-400/35";
    default:
      return "bg-emerald-500/20 text-emerald-100 ring-emerald-400/35";
  }
}

function avatarInitial(displayName: string, email: string): string {
  const source = displayName.trim() || email.trim();
  return (source.charAt(0) || "?").toUpperCase();
}

function formatPaymentDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat("es", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function formatAmount(amount: number): string {
  return new Intl.NumberFormat("es-CL", {
    style: "currency",
    currency: "CLP",
    maximumFractionDigits: 0,
  }).format(amount);
}

function paymentStatusLabel(status: PaymentHistoryItem["status"]): string {
  switch (status) {
    case "approved":
      return "Aprobado";
    case "rejected":
      return "Rechazado";
    default:
      return "Pendiente";
  }
}

function paymentStatusClasses(status: PaymentHistoryItem["status"]): string {
  switch (status) {
    case "approved":
      return "bg-emerald-500/15 text-emerald-200 ring-emerald-400/30";
    case "rejected":
      return "bg-red-500/15 text-red-200 ring-red-400/30";
    default:
      return "bg-amber-500/15 text-amber-200 ring-amber-400/30";
  }
}

export function ProfilePage() {
  const router = useRouter();
  const { user, accessToken, isLoading, logout, refreshUser } = useAuth();

  const [displayName, setDisplayName] = useState("");
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileNotice, setProfileNotice] = useState<string | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [passwordNotice, setPasswordNotice] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  const [payments, setPayments] = useState<PaymentHistoryItem[]>([]);
  const [paymentsLoading, setPaymentsLoading] = useState(false);
  const [paymentsError, setPaymentsError] = useState<string | null>(null);

  const tier = normalizeTier(user?.tier);

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  useEffect(() => {
    if (user?.display_name) {
      setDisplayName(user.display_name);
    }
  }, [user?.display_name]);

  const loadPayments = useCallback(async () => {
    if (!accessToken) {
      return;
    }
    setPaymentsLoading(true);
    setPaymentsError(null);
    try {
      const data = await fetchPaymentHistory(accessToken);
      setPayments(data.items);
    } catch (err) {
      setPaymentsError(err instanceof Error ? err.message : "Error al cargar pagos.");
    } finally {
      setPaymentsLoading(false);
    }
  }, [accessToken]);

  useEffect(() => {
    void loadPayments();
  }, [loadPayments]);

  async function onProfileSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken || !displayName.trim()) {
      return;
    }

    setProfileSaving(true);
    setProfileNotice(null);
    setProfileError(null);

    try {
      await updateProfileRequest(accessToken, displayName);
      await refreshUser();
      setProfileNotice("Nombre actualizado correctamente.");
    } catch (err) {
      setProfileError(err instanceof Error ? err.message : "No se pudo guardar.");
    } finally {
      setProfileSaving(false);
    }
  }

  async function onPasswordSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken) {
      return;
    }

    setPasswordNotice(null);
    setPasswordError(null);

    if (newPassword.length < 8) {
      setPasswordError("La nueva contraseña debe tener al menos 8 caracteres.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError("Las contraseñas nuevas no coinciden.");
      return;
    }

    setPasswordSaving(true);
    try {
      await changePasswordRequest(accessToken, currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setPasswordNotice("Contraseña actualizada correctamente.");
    } catch (err) {
      setPasswordError(err instanceof Error ? err.message : "No se pudo cambiar la contraseña.");
    } finally {
      setPasswordSaving(false);
    }
  }

  if (isLoading || !user) {
    return (
      <PageShell>
        <div className="mx-auto max-w-3xl px-4 py-20 text-center text-zinc-400 sm:px-8">
          Cargando perfil...
        </div>
      </PageShell>
    );
  }

  return (
    <PageShell>
      <div className="mx-auto max-w-3xl px-4 py-10 sm:px-8 sm:py-14">
        <div className="mb-8">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-violet-400/90">
            Tu cuenta
          </p>
          <h1 className="mt-2 text-3xl font-black tracking-tight text-white sm:text-4xl">
            Perfil
          </h1>
          <p className="mt-2 text-sm text-zinc-400">
            Administra tu nombre, contraseña y revisa tu plan activo.
          </p>
        </div>

        <section className="mb-6 overflow-hidden rounded-2xl border border-white/10 bg-zinc-950/55 p-6 shadow-[0_0_60px_-20px_rgba(139,92,246,0.45)] backdrop-blur-xl sm:p-8">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-4">
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-500/30 to-violet-500/30 text-xl font-black text-white ring-1 ring-white/15">
                {avatarInitial(user.display_name, user.email)}
              </div>
              <div className="min-w-0">
                <p className="truncate text-lg font-bold text-white">
                  {user.display_name || user.email}
                </p>
                <p className="truncate text-sm text-zinc-400">{user.email}</p>
              </div>
            </div>
            <span
              className={`inline-flex w-fit rounded-lg px-3 py-1 text-xs font-bold uppercase tracking-wide ring-1 ${tierBadgeClasses(tier)}`}
            >
              {user.tier_label || tierLabel(tier)}
            </span>
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            {!isPaidTier(tier) ? (
              <Link
                href="/planes"
                className="inline-flex rounded-xl bg-gradient-to-r from-cyan-500 to-violet-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:opacity-90"
              >
                Mejorar plan
              </Link>
            ) : (
              <Link
                href="/planes"
                className="inline-flex rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm font-medium text-zinc-200 transition hover:bg-white/10"
              >
                Ver planes
              </Link>
            )}
            <button
              type="button"
              onClick={logout}
              className="inline-flex rounded-xl border border-white/10 px-4 py-2.5 text-sm font-medium text-zinc-300 transition hover:bg-white/5 hover:text-white"
            >
              Cerrar sesión
            </button>
          </div>
        </section>

        <section className="mb-6 rounded-2xl border border-white/10 bg-zinc-950/55 p-6 backdrop-blur-xl sm:p-8">
          <h2 className="text-lg font-bold text-white">Datos personales</h2>
          <p className="mt-1 text-sm text-zinc-400">El correo no se puede cambiar desde aquí.</p>

          <form className="mt-6 space-y-5" onSubmit={onProfileSubmit}>
            <label className="block space-y-2">
              <span className="text-sm text-zinc-300">Correo</span>
              <input
                type="email"
                value={user.email}
                disabled
                className="w-full cursor-not-allowed rounded-xl border border-white/10 bg-black/25 px-4 py-3 text-zinc-500"
              />
            </label>

            <label className="block space-y-2">
              <span className="text-sm text-zinc-300">Nombre visible</span>
              <input
                type="text"
                required
                maxLength={128}
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-black/40 px-4 py-3 text-white outline-none ring-cyan-500/40 focus:ring-2"
                placeholder="Tu nombre"
                autoComplete="name"
              />
            </label>

            {profileError ? (
              <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                {profileError}
              </p>
            ) : null}
            {profileNotice ? (
              <p className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
                {profileNotice}
              </p>
            ) : null}

            <button
              type="submit"
              disabled={profileSaving || displayName.trim() === user.display_name}
              className="rounded-xl bg-gradient-to-r from-cyan-500 to-violet-500 px-5 py-2.5 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {profileSaving ? "Guardando..." : "Guardar cambios"}
            </button>
          </form>
        </section>

        <section className="mb-6 rounded-2xl border border-white/10 bg-zinc-950/55 p-6 backdrop-blur-xl sm:p-8">
          <h2 className="text-lg font-bold text-white">Seguridad</h2>
          <p className="mt-1 text-sm text-zinc-400">Cambia tu contraseña cuando lo necesites.</p>

          <form className="mt-6 space-y-5" onSubmit={onPasswordSubmit}>
            <label className="block space-y-2">
              <span className="text-sm text-zinc-300">Contraseña actual</span>
              <input
                type="password"
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-black/40 px-4 py-3 text-white outline-none ring-cyan-500/40 focus:ring-2"
                autoComplete="current-password"
              />
            </label>

            <label className="block space-y-2">
              <span className="text-sm text-zinc-300">Nueva contraseña</span>
              <input
                type="password"
                required
                minLength={8}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-black/40 px-4 py-3 text-white outline-none ring-cyan-500/40 focus:ring-2"
                placeholder="Mínimo 8 caracteres"
                autoComplete="new-password"
              />
            </label>

            <label className="block space-y-2">
              <span className="text-sm text-zinc-300">Confirmar nueva contraseña</span>
              <input
                type="password"
                required
                minLength={8}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-black/40 px-4 py-3 text-white outline-none ring-cyan-500/40 focus:ring-2"
                autoComplete="new-password"
              />
            </label>

            {passwordError ? (
              <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                {passwordError}
              </p>
            ) : null}
            {passwordNotice ? (
              <p className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
                {passwordNotice}
              </p>
            ) : null}

            <button
              type="submit"
              disabled={passwordSaving}
              className="rounded-xl border border-white/10 bg-white/5 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {passwordSaving ? "Actualizando..." : "Cambiar contraseña"}
            </button>
          </form>
        </section>

        <section className="rounded-2xl border border-white/10 bg-zinc-950/55 p-6 backdrop-blur-xl sm:p-8">
          <h2 className="text-lg font-bold text-white">Historial de pagos</h2>
          <p className="mt-1 text-sm text-zinc-400">Transacciones Webpay asociadas a tu cuenta.</p>

          <div className="mt-6">
            {paymentsLoading ? (
              <p className="text-sm text-zinc-500">Cargando pagos...</p>
            ) : paymentsError ? (
              <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                {paymentsError}
              </p>
            ) : payments.length === 0 ? (
              <p className="rounded-xl border border-white/10 bg-black/25 px-4 py-6 text-center text-sm text-zinc-500">
                Aún no tienes pagos registrados.
              </p>
            ) : (
              <ul className="divide-y divide-white/10 rounded-xl border border-white/10 bg-black/25">
                {payments.map((payment) => (
                  <li
                    key={payment.id}
                    className="flex flex-col gap-2 px-4 py-4 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div>
                      <p className="text-sm font-semibold capitalize text-white">
                        Plan {payment.plan}
                      </p>
                      <p className="text-xs text-zinc-500">
                        {formatPaymentDate(payment.created_at)}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium text-zinc-200">
                        {formatAmount(payment.amount)}
                      </span>
                      <span
                        className={`rounded-md px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ring-1 ${paymentStatusClasses(payment.status)}`}
                      >
                        {paymentStatusLabel(payment.status)}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      </div>
    </PageShell>
  );
}

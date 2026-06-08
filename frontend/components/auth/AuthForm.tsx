"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { useAuth } from "./AuthProvider";

type AuthFormProps = {
  mode: "login" | "register";
};

export function AuthForm({ mode }: AuthFormProps) {
  const router = useRouter();
  const { login, register } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const isRegister = mode === "register";

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      if (isRegister) {
        await register(email, password, displayName);
      } else {
        await login(email, password);
      }
      router.push("/");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error inesperado.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="relative mx-auto w-full max-w-md overflow-hidden rounded-2xl border border-white/10 bg-zinc-950/55 p-8 shadow-[0_0_80px_-24px_rgba(139,92,246,0.65)] backdrop-blur-xl">
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cyan-400/60 to-transparent"
        aria-hidden
      />
      <h2 className="mb-2 text-xl font-bold text-white">
        {isRegister ? "Crear cuenta" : "Iniciar sesión"}
      </h2>
      <p className="mb-8 text-sm text-zinc-400">
        {isRegister
          ? "Regístrate para guardar tu progreso y acceder a funciones premium."
          : "Accede con tu correo y contraseña."}
      </p>

      <form className="space-y-5" onSubmit={onSubmit}>
        {isRegister ? (
          <label className="block space-y-2">
            <span className="text-sm text-zinc-300">Nombre</span>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full rounded-xl border border-white/10 bg-black/40 px-4 py-3 text-white outline-none ring-cyan-500/40 focus:ring-2"
              placeholder="Tu nombre"
              autoComplete="name"
            />
          </label>
        ) : null}

        <label className="block space-y-2">
          <span className="text-sm text-zinc-300">Correo</span>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-xl border border-white/10 bg-black/40 px-4 py-3 text-white outline-none ring-cyan-500/40 focus:ring-2"
            placeholder="tu@correo.com"
            autoComplete="email"
          />
        </label>

        <label className="block space-y-2">
          <span className="text-sm text-zinc-300">Contraseña</span>
          <input
            type="password"
            required
            minLength={isRegister ? 8 : 1}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-xl border border-white/10 bg-black/40 px-4 py-3 text-white outline-none ring-cyan-500/40 focus:ring-2"
            placeholder={isRegister ? "Mínimo 8 caracteres" : "Tu contraseña"}
            autoComplete={isRegister ? "new-password" : "current-password"}
          />
        </label>

        {error ? (
          <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {error}
          </p>
        ) : null}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-xl bg-gradient-to-r from-cyan-500 to-violet-500 px-4 py-3 font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {submitting ? "Procesando..." : isRegister ? "Registrarme" : "Entrar"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-zinc-400">
        {isRegister ? "¿Ya tienes cuenta?" : "¿No tienes cuenta?"}{" "}
        <Link
          href={isRegister ? "/login" : "/register"}
          className="font-medium text-cyan-300 hover:text-cyan-200"
        >
          {isRegister ? "Inicia sesión" : "Regístrate"}
        </Link>
      </p>
    </div>
  );
}

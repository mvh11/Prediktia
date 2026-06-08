import { AuthForm } from "@/components/auth/AuthForm";

export default function LoginPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-violet-950/40 via-[#050508] to-black px-4 py-12">
      <div className="mb-8 text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-violet-400/85">
          Prediktia Intelligence
        </p>
        <h1 className="mt-2 bg-gradient-to-r from-cyan-300 to-violet-300 bg-clip-text text-3xl font-black text-transparent">
          Bienvenido
        </h1>
        <p className="mt-2 text-sm text-zinc-500">Inicia sesión para acceder a la plataforma</p>
      </div>
      <AuthForm mode="login" />
    </div>
  );
}

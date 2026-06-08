import type { ReactNode } from "react";

type AuthLayoutProps = {
  title: string;
  subtitle: string;
  children: ReactNode;
};

export function AuthLayout({ title, subtitle, children }: AuthLayoutProps) {
  return (
    <div className="auth-scene relative min-h-screen overflow-hidden bg-[#030308]">
      <div className="auth-grid pointer-events-none absolute inset-0 opacity-[0.35]" aria-hidden />
      <div className="auth-orb auth-orb-cyan pointer-events-none absolute -left-24 top-[-8rem] h-[28rem] w-[28rem] rounded-full blur-3xl" aria-hidden />
      <div className="auth-orb auth-orb-violet pointer-events-none absolute -right-20 top-[12%] h-[24rem] w-[24rem] rounded-full blur-3xl" aria-hidden />
      <div className="auth-orb auth-orb-fuchsia pointer-events-none absolute bottom-[-6rem] left-[20%] h-[22rem] w-[22rem] rounded-full blur-3xl" aria-hidden />

      <div className="relative z-10 flex min-h-screen flex-col items-center justify-center px-4 py-12">
        <div className="mb-8 animate-home-fade text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-violet-400/90">
            Prediktia Intelligence
          </p>
          <h1 className="mt-3 bg-gradient-to-r from-cyan-200 via-white to-violet-300 bg-clip-text text-4xl font-black tracking-tight text-transparent sm:text-5xl">
            {title}
          </h1>
          <p className="mx-auto mt-3 max-w-sm text-sm leading-relaxed text-zinc-400">{subtitle}</p>
        </div>

        <div className="animate-home-fade w-full max-w-md" style={{ animationDelay: "120ms" }}>
          {children}
        </div>

        <p
          className="animate-home-fade mt-10 text-center text-[11px] uppercase tracking-[0.2em] text-zinc-600"
          style={{ animationDelay: "220ms" }}
        >
          Análisis · Value · ACCA
        </p>
      </div>
    </div>
  );
}

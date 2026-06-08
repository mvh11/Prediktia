import type { ReactNode } from "react";

type PageShellProps = {
  children: ReactNode;
  className?: string;
};

/**
 * Fondo unificado (Home / Planes): oscuro + gradientes cyan/violeta.
 */
export function PageShell({ children, className = "" }: PageShellProps) {
  return (
    <div className={`relative min-h-full overflow-hidden bg-[#050508] text-white ${className}`}>
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_120%_80%_at_50%_-20%,rgba(124,58,237,0.22),transparent_55%),radial-gradient(ellipse_80%_50%_at_100%_0%,rgba(6,182,212,0.12),transparent_45%),radial-gradient(ellipse_60%_40%_at_0%_100%,rgba(236,72,153,0.08),transparent_40%)]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute inset-0 bg-[linear-gradient(180deg,rgba(255,255,255,0.03)_0%,transparent_28%,transparent_100%)]"
        aria-hidden
      />
      <div className="relative">{children}</div>
    </div>
  );
}

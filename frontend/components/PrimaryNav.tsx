"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Home" },
  { href: "/matches", label: "Partidos" },
  { href: "/value", label: "Value" },
  { href: "/acca", label: "ACCA" },
  { href: "/planes", label: "Planes" },
  { href: "/legal", label: "Legal" },
] as const;

function linkIsActive(pathname: string, href: string) {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function PrimaryNav() {
  const pathname = usePathname();

  return (
    <nav className="sticky top-0 z-50 border-b border-white/[0.06] bg-[#050508]/80 px-4 py-3 backdrop-blur-xl sm:px-8 sm:py-3.5 lg:px-10">
      <div className="mx-auto flex max-w-7xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
        <Link
          href="/"
          className="text-lg font-black tracking-tight text-white transition hover:text-cyan-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-500/60 sm:text-xl"
        >
          <span className="bg-gradient-to-r from-cyan-300 to-violet-300 bg-clip-text text-transparent">PREDIKTIA</span>
        </Link>

        <ul className="flex flex-wrap items-center gap-x-1 gap-y-1 sm:justify-end sm:gap-x-0.5">
          {links.map(({ href, label }) => {
            const active = linkIsActive(pathname, href);
            return (
              <li key={href}>
                <Link
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className={[
                    "relative inline-flex rounded-lg px-2.5 py-2 text-sm transition sm:px-3",
                    active
                      ? "font-semibold text-white"
                      : "font-medium text-zinc-400 hover:text-white",
                  ].join(" ")}
                >
                  <span
                    className={[
                      "rounded-md px-1.5 py-1 transition-colors sm:px-2",
                      active
                        ? "bg-white/10 ring-1 ring-violet-500/40 shadow-[0_0_20px_-6px_rgba(139,92,246,0.5)]"
                        : "hover:bg-white/5 hover:ring-1 hover:ring-white/10",
                    ].join(" ")}
                  >
                    {label}
                  </span>
                  {active ? (
                    <span
                      className="pointer-events-none absolute inset-x-2 -bottom-0.5 h-0.5 rounded-full bg-gradient-to-r from-transparent via-violet-400 to-cyan-400 opacity-90 sm:inset-x-3"
                      aria-hidden
                    />
                  ) : null}
                </Link>
              </li>
            );
          })}
        </ul>
      </div>
    </nav>
  );
}

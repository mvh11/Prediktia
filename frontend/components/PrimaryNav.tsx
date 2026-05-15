"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Home" },
  { href: "/matches", label: "Partidos" },
  { href: "/value", label: "Value" },
  { href: "/acca", label: "ACCA" },
  { href: "/planes", label: "Planes" },
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
    <nav className="border-b border-gray-800 bg-gray-900 px-4 py-3 sm:px-8 lg:px-10 sm:py-4">
      <div className="mx-auto flex max-w-7xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
        <Link
          href="/"
          className="text-xl font-bold text-cyan-400 transition hover:text-cyan-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-500/60"
        >
          PREDIKTIA
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
                      ? "font-semibold text-cyan-300"
                      : "font-medium text-gray-300 hover:text-cyan-400",
                  ].join(" ")}
                >
                  <span
                    className={[
                      "rounded-md px-1.5 py-1 transition-colors sm:px-2",
                      active
                        ? "bg-cyan-500/15 ring-1 ring-cyan-500/35"
                        : "hover:bg-white/5 hover:ring-1 hover:ring-white/10",
                    ].join(" ")}
                  >
                    {label}
                  </span>
                  {active ? (
                    <span
                      className="pointer-events-none absolute inset-x-2 -bottom-0.5 h-0.5 rounded-full bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-90 sm:inset-x-3"
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

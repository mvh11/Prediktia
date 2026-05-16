"use client";

import { useEffect, useState } from "react";

const ITEMS = [
  {
    quote: "Por primera vez veo transparencia real en apuestas.",
    author: "Marina R.",
    role: "Trader deportivo",
    rating: 5,
  },
  {
    quote: "El EV y el historial ayudan mucho a decidir sin ir a ciegas.",
    author: "Diego P.",
    role: "Usuario Plus",
    rating: 5,
  },
  {
    quote: "La gestión de riesgo en el ACCA está muy bien pensada.",
    author: "Lucas G.",
    role: "Apostador semi-pro",
    rating: 5,
  },
  {
    quote: "Los datos del partido y la liga se entienden al instante.",
    author: "Valentina S.",
    role: "Fan de datos",
    rating: 5,
  },
  {
    quote: "Combina lo mejor de stats y una UX que no cansa.",
    author: "Andrés M.",
    role: "Product designer",
    rating: 5,
  },
] as const;

export function TestimonialCarousel() {
  const [i, setI] = useState(0);

  useEffect(() => {
    const t = setInterval(() => {
      setI((n) => (n + 1) % ITEMS.length);
    }, 5200);
    return () => clearInterval(t);
  }, []);

  const cur = ITEMS[i];

  return (
    <div className="relative mx-auto max-w-3xl">
      <div className="pointer-events-none absolute -inset-px rounded-3xl bg-gradient-to-br from-violet-500/25 via-transparent to-cyan-500/20 opacity-80 blur-xl" />
      <div className="relative overflow-hidden rounded-3xl border border-white/[0.08] bg-zinc-900/70 px-8 py-10 shadow-[0_0_0_1px_rgba(255,255,255,0.04)] backdrop-blur-xl sm:px-12 sm:py-12">
        <div className="mb-6 flex items-center justify-center gap-1">
          {Array.from({ length: cur.rating }).map((_, k) => (
            <span key={k} className="text-amber-400 drop-shadow-[0_0_8px_rgba(251,191,36,0.35)]">
              ★
            </span>
          ))}
        </div>
        <blockquote className="text-center text-lg font-medium leading-relaxed text-zinc-100 sm:text-xl">
          “{cur.quote}”
        </blockquote>
        <div className="mt-8 flex flex-col items-center gap-1">
          <div className="flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-br from-violet-500/40 to-cyan-500/30 text-sm font-bold text-white ring-2 ring-white/10">
            {cur.author
              .split(" ")
              .map((w) => w[0])
              .join("")}
          </div>
          <p className="text-sm font-semibold text-white">{cur.author}</p>
          <p className="text-xs text-zinc-500">{cur.role}</p>
        </div>
        <div className="mt-8 flex justify-center gap-2">
          {ITEMS.map((_, idx) => (
            <button
              key={idx}
              type="button"
              aria-label={`Testimonio ${idx + 1}`}
              onClick={() => setI(idx)}
              className={[
                "h-2 rounded-full transition-all duration-300",
                idx === i ? "w-8 bg-cyan-400 shadow-[0_0_12px_rgba(34,211,238,0.45)]" : "w-2 bg-zinc-600 hover:bg-zinc-500",
              ].join(" ")}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

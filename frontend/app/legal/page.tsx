import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Legal · Prediktia",
  description: "Aviso legal, uso responsable y limitación de responsabilidad.",
};

const sections = [
  {
    title: "Naturaleza del servicio",
    body: "Prediktia es una herramienta de apoyo estadístico basada en inteligencia artificial y datos deportivos. No constituye asesoría financiera, legal ni recomendación de inversión.",
  },
  {
    title: "Sin garantía de resultados",
    body: "Las probabilidades, predicciones, métricas de valor esperado (EV) y combinadas generadas son estimaciones modeladas. No garantizan aciertos ni resultados favorables en apuestas deportivas.",
  },
  {
    title: "Uso responsable",
    body: "Las apuestas implican riesgo económico. Prediktia no promueve apuestas irresponsables. Utiliza la plataforma con criterio, dentro de tus posibilidades y cumpliendo la normativa local aplicable.",
  },
  {
    title: "Limitación de responsabilidad",
    body: "Prediktia y sus desarrolladores no se hacen responsables por pérdidas, decisiones de apuesta ni daños derivados del uso de la información mostrada. El usuario es el único responsable de sus decisiones.",
  },
  {
    title: "Mayores de 18 años",
    body: "El acceso y uso de Prediktia están dirigidos exclusivamente a personas mayores de 18 años en jurisdicciones donde las apuestas deportivas estén permitidas.",
  },
  {
    title: "Datos y terceros",
    body: "Los datos deportivos provienen de proveedores externos (p. ej. API-Football). Pueden existir retrasos, errores o cambios de calendario que afecten la información mostrada.",
  },
] as const;

export default function LegalPage() {
  return (
    <div className="min-h-full bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-violet-950/25 via-zinc-950 to-black pb-24 pt-10 text-white">
      <div className="mx-auto max-w-3xl px-4 sm:px-6">
        <header className="mb-12">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-violet-400/85">
            Prediktia
          </p>
          <h1 className="mt-2 text-3xl font-black tracking-tight text-white sm:text-4xl">
            Aviso legal
          </h1>
          <p className="mt-4 text-sm leading-relaxed text-zinc-400">
            Información importante sobre el alcance de la plataforma, el riesgo asociado a las
            apuestas y el uso responsable de las herramientas estadísticas.
          </p>
        </header>

        <div className="mb-8 rounded-2xl border border-amber-500/30 bg-amber-500/10 px-5 py-4 text-sm text-amber-50">
          <strong className="font-semibold">+18</strong> · Prediktia no garantiza ganancias ni
          entrega asesoría financiera. Las predicciones no aseguran resultados deportivos.
        </div>

        <div className="space-y-6">
          {sections.map((s) => (
            <section
              key={s.title}
              className="rounded-2xl border border-white/10 bg-zinc-900/50 p-6 backdrop-blur-sm"
            >
              <h2 className="text-lg font-bold text-white">{s.title}</h2>
              <p className="mt-3 text-sm leading-relaxed text-zinc-400">{s.body}</p>
            </section>
          ))}
        </div>

        <p className="mt-10 text-center text-xs text-zinc-600">
          Última actualización: demo académica · Prediktia Intelligence
        </p>
      </div>
    </div>
  );
}

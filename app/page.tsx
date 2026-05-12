{/* Home */}
import Link from "next/link";

export default function Home() {
  return (
    <div className="bg-gray-950 text-white min-h-screen p-10">

      {/* HERO */}
      <section className="grid md:grid-cols-2 gap-8 mt-6">

        {/* LEFT CARD */}
        <div className="relative rounded-2xl p-[2px] bg-gradient-to-r from-cyan-500 via-blue-500 to-green-400">

          <div className="absolute inset-0 blur-xl opacity-30 bg-gradient-to-r from-cyan-500 via-blue-500 to-green-400 rounded-2xl"></div>

          <div className="relative bg-gray-900 rounded-2xl p-8">

            <h1 className="text-4xl font-bold mb-4">Prediktia</h1>

            <p className="text-gray-400 mb-6">
              Predicciones deportivas con IA · Transparencia · Valor esperado · Control de riesgo
            </p>

            {/* KPIs */}
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="bg-gray-800 p-4 rounded-xl border border-gray-700">
                <p className="text-sm text-gray-400">ROI</p>
                <h2 className="text-xl text-green-400 font-bold">8.4%</h2>
              </div>
              <div className="bg-gray-800 p-4 rounded-xl border border-gray-700">
                <p className="text-sm text-gray-400">Hitrate</p>
                <h2 className="text-xl text-blue-400 font-bold">57%</h2>
              </div>
              <div className="bg-gray-800 p-4 rounded-xl border border-gray-700">
                <p className="text-sm text-gray-400">Ligas</p>
                <h2 className="text-xl text-yellow-400 font-bold">18</h2>
              </div>
            </div>

            {/* BOTONES */}
            <div className="flex gap-4">

              <button className="px-6 py-3 rounded-xl font-semibold text-black bg-green-400 hover:bg-green-300 shadow-lg shadow-green-500/50 hover:shadow-green-400/80 transition">
                Ver predicciones →
              </button>
            {/* BOTON DE PREMIUM ESTE BOTON NOS MANDA A PLANEES */}
            <Link 
              href="/planes"
              className="px-6 py-3 rounded-xl font-semibold text-white bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 shadow-lg shadow-cyan-500/50 hover:shadow-cyan-400/80 transition"
            >
              Hazte Premium 👑
            </Link>
            </div>

          </div>
        </div>

        {/* ACCA CARD */}
        <div className="relative rounded-2xl p-[2px] bg-gradient-to-r from-purple-500 to-pink-500">

          <div className="absolute inset-0 blur-xl opacity-30 bg-gradient-to-r from-purple-500 to-pink-500 rounded-2xl"></div>

          <div className="relative bg-gray-900 rounded-2xl p-8">

            <h3 className="text-xl font-semibold mb-2">Smart ACCA Builder</h3>

            <p className="text-gray-400 mb-4">
              Genera combinadas según tu perfil de riesgo.
            </p>

            <select className="w-full p-2 rounded bg-gray-800 mb-4">
              <option>Bajo</option>
              <option>Medio</option>
              <option>Alto</option>
            </select>

            <button className="w-full py-3 rounded-xl bg-gradient-to-r from-purple-500 to-pink-500 shadow-lg shadow-purple-500/50 hover:shadow-purple-400/80 transition">
              Generar combinada ✨
            </button>

            <p className="text-xs text-gray-500 mt-4">
              EV = prob × cuota → valor positivo si &gt; 1
            </p>

          </div>
        </div>

      </section>

      {/* FEATURES */}
      <section className="grid md:grid-cols-3 gap-6 mt-16">

        <div className="bg-gray-900 p-6 rounded-xl border border-gray-800 hover:border-cyan-400 transition">
          <h3 className="text-lg font-semibold mb-2">📊 Datos reales</h3>
          <p className="text-gray-400 text-sm">
            Modelos Poisson/Elo + contexto en vivo.
          </p>
        </div>

        <div className="bg-gray-900 p-6 rounded-xl border border-gray-800 hover:border-purple-400 transition">
          <h3 className="text-lg font-semibold mb-2">⚡ ACCA inteligente</h3>
          <p className="text-gray-400 text-sm">
            Riesgo optimizado y valor esperado.
          </p>
        </div>

        <div className="bg-gray-900 p-6 rounded-xl border border-gray-800 hover:border-green-400 transition">
          <h3 className="text-lg font-semibold mb-2">🛡️ Transparencia</h3>
          <p className="text-gray-400 text-sm">
            Métricas públicas sin humo.
          </p>
        </div>

      </section>

      {/* TESTIMONIOS (aqui testimonios)*/}
      <section className="mt-16">

        <h2 className="text-2xl font-bold mb-6">Lo que dicen los usuarios</h2>

        <div className="grid md:grid-cols-3 gap-6">

          <div className="bg-gray-900 p-4 rounded-xl border border-gray-800">
            <p className="text-gray-400 text-sm">“Interfaz top.”</p>
            <span className="text-xs text-gray-500">— Carlos</span>
          </div>

          <div className="bg-gray-900 p-4 rounded-xl border border-gray-800">
            <p className="text-gray-400 text-sm">“Muy buenos datos.”</p>
            <span className="text-xs text-gray-500">— Belén</span>
          </div>

          <div className="bg-gray-900 p-4 rounded-xl border border-gray-800">
            <p className="text-gray-400 text-sm">“El ACCA es brutal.”</p>
            <span className="text-xs text-gray-500">— Tomás</span>
          </div>

          <div className="bg-gray-900 p-4 rounded-xl border border-gray-800">
            <p className="text-gray-400 text-sm">“Muy lindos los programadores.”</p>
            <span className="text-xs text-gray-500">— Maximiliano</span>
          </div>

          <div className="bg-gray-900 p-4 rounded-xl border border-gray-800">
            <p className="text-gray-400 text-sm">“Acabo de ganar mi sueldo en un dia gracias a PREDIKTIA.”</p>
            <span className="text-xs text-gray-500">— Elias</span>
          </div>

        </div>

      </section>

    </div>
  );
}

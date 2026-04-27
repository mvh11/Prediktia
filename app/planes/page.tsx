export default function Planes() {
  return (
    <div className="bg-gray-950 text-white min-h-screen p-10">

      <h1 className="text-3xl font-bold mb-10">Planes</h1>

      <div className="flex flex-col gap-8">

        {/* FREE */}
        <div className="relative rounded-2xl p-[2px] bg-gradient-to-r from-green-400 to-cyan-500">

          <div className="absolute inset-0 blur-xl opacity-30 bg-gradient-to-r from-green-400 to-cyan-500 rounded-2xl"></div>

          <div className="relative bg-gray-900 p-8 rounded-2xl flex justify-between items-center">

            <div>
              <h2 className="text-xl font-semibold mb-2">Free</h2>
              <p className="text-gray-400">3 picks/día. Sin ACCA.</p>
            </div>

            <button className="px-6 py-3 rounded-xl bg-green-400 text-black font-semibold hover:bg-green-300 shadow-lg shadow-green-500/50 transition">
              Empezar
            </button>

          </div>
        </div>

        {/* PREMIUM */}
        <div className="relative rounded-2xl p-[2px] bg-gradient-to-r from-cyan-500 to-blue-500">

          <div className="absolute inset-0 blur-xl opacity-30 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-2xl"></div>

          <div className="relative bg-gray-900 p-8 rounded-2xl flex justify-between items-center">

            <div>
              <h2 className="text-xl font-semibold mb-2">Premium</h2>
              <p className="text-gray-400">
                Predicciones completas, Value y Smart ACCA.
              </p>
            </div>

            <button className="px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-500 text-white font-semibold shadow-lg shadow-cyan-500/50 hover:shadow-cyan-400/80 transition">
              Hazte Premium
            </button>

          </div>
        </div>

        {/* VIP */}
        <div className="relative rounded-2xl p-[2px] bg-gradient-to-r from-purple-500 to-pink-500">

          <div className="absolute inset-0 blur-xl opacity-30 bg-gradient-to-r from-purple-500 to-pink-500 rounded-2xl"></div>

          <div className="relative bg-gray-900 p-8 rounded-2xl flex justify-between items-center">

            <div>
              <h2 className="text-xl font-semibold mb-2">VIP</h2>
              <p className="text-gray-400">
                Personalización y métricas avanzadas.
              </p>
            </div>

            <button className="px-6 py-3 rounded-xl bg-purple-500 text-white font-semibold shadow-lg shadow-purple-500/50 hover:shadow-purple-400/80 transition">
              Contactar
            </button>

          </div>
        </div>

      </div>

    </div>
  );
}

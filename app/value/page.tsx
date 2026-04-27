export default function Value() {
  const data = [
    {
      liga: "Serie A",
      partido: "Atalanta vs Torino",
      mercado: "Over 2.5",
      pick: "Over",
      prob: 0.54,
      cuota: 2.05,
    },
    {
      liga: "LaLiga",
      partido: "Betis vs Girona",
      mercado: "BTTS",
      pick: "Yes",
      prob: 0.55,
      cuota: 1.95,
    },
        {
      liga: "Bundesliga",
      partido: "Bayern de Múnich vs Mainz",
      mercado: "Over 2.5",
      pick: "Over",
      prob: 0.71,
      cuota: 1.99,
    },
  ];

  return (
    <div className="bg-gray-950 text-white min-h-screen p-10">

      <h1 className="text-2xl font-bold mb-6">
        Apuestas con valor (ordenadas por edge)
      </h1>

      {/* CONTENEDOR */}
      <div className="relative rounded-2xl p-[2px] bg-gradient-to-r from-cyan-500 to-green-400">

        <div className="absolute inset-0 blur-xl opacity-30 bg-gradient-to-r from-cyan-500 to-green-400 rounded-2xl"></div>

        <div className="relative bg-gray-900 rounded-2xl overflow-hidden">

          {/* HEADER */}
          <div className="grid grid-cols-7 px-6 py-4 text-gray-400 text-sm border-b border-gray-800">
            <span>Liga</span>
            <span>Partido</span>
            <span>Mercado</span>
            <span>Pick</span>
            <span>Prob</span>
            <span>Cuota</span>
            <span>Edge</span>
          </div>

          {/* FILAS */}
          {data.map((item, index) => {
            const edge = (item.prob * item.cuota - 1).toFixed(2);
            const positivo = parseFloat(edge) > 0;

            return (
              <div
                key={index}
                className="grid grid-cols-7 px-6 py-4 items-center border-b border-gray-800 hover:bg-gray-800/50 transition"
              >

                {/* LIGA */}
                <span className="text-xs bg-gray-800 px-3 py-1 rounded-full w-fit">
                  {item.liga}
                </span>

                {/* PARTIDO */}
                <span>{item.partido}</span>

                {/* MERCADO */}
                <span className="text-gray-400">{item.mercado}</span>

                {/* PICK */}
                <span className="font-semibold">{item.pick}</span>

                {/* PROB */}
                <span>{item.prob}</span>

                {/* CUOTA */}
                <span>{item.cuota}</span>

                {/* EDGE */}
                <span
                  className={`px-3 py-1 rounded-full text-xs font-semibold w-fit ${
                    positivo
                      ? "bg-green-500/20 text-green-400"
                      : "bg-red-500/20 text-red-400"
                  }`}
                >
                  {positivo ? "+" : ""}
                  {edge}
                </span>

              </div>
            );
          })}

        </div>
      </div>

    </div>
  );
}

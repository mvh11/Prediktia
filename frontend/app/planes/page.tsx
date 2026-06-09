import { Suspense } from "react";

import { PlansPage } from "@/components/plans/PlansPage";

export const metadata = {
  title: "Planes",
};

function PlansFallback() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#050508] text-zinc-500">
      Cargando planes…
    </div>
  );
}

export default function PlanesRoute() {
  return (
    <Suspense fallback={<PlansFallback />}>
      <PlansPage />
    </Suspense>
  );
}

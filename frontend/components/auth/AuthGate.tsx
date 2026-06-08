"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { useAuth } from "./AuthProvider";

const PUBLIC_PATHS = new Set(["/login", "/register"]);

export function AuthGate({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const isPublic = PUBLIC_PATHS.has(pathname);

  useEffect(() => {
    if (isLoading) {
      return;
    }
    if (!user && !isPublic) {
      router.replace("/login");
      return;
    }
    if (user && isPublic) {
      router.replace("/");
    }
  }, [isLoading, user, isPublic, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#050508] text-zinc-400">
        Cargando…
      </div>
    );
  }

  if (!user && !isPublic) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#050508] text-zinc-400">
        Redirigiendo al login…
      </div>
    );
  }

  if (user && isPublic) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#050508] text-zinc-400">
        Redirigiendo…
      </div>
    );
  }

  return <>{children}</>;
}

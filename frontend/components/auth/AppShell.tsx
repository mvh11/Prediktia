"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { PrimaryNav } from "@/components/PrimaryNav";

import { AuthGate } from "./AuthGate";
import { useAuth } from "./AuthProvider";

const PUBLIC_PATHS = new Set(["/login", "/register"]);

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { isLoading } = useAuth();
  const isPublic = PUBLIC_PATHS.has(pathname);

  return (
    <AuthGate>
      {!isLoading && !isPublic ? <PrimaryNav /> : null}
      <main className="flex-1">{children}</main>
    </AuthGate>
  );
}

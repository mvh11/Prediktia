import { AuthForm } from "@/components/auth/AuthForm";
import { AuthLayout } from "@/components/auth/AuthLayout";

export default function LoginPage() {
  return (
    <AuthLayout
      title="Bienvenido"
      subtitle="Inicia sesión para acceder a predicciones, value bets y tu historial ACCA."
    >
      <AuthForm mode="login" />
    </AuthLayout>
  );
}

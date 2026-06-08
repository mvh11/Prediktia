import { AuthForm } from "@/components/auth/AuthForm";
import { AuthLayout } from "@/components/auth/AuthLayout";

export default function RegisterPage() {
  return (
    <AuthLayout
      title="Crear cuenta"
      subtitle="Únete a Prediktia y guarda tus combinadas en tu perfil."
    >
      <AuthForm mode="register" />
    </AuthLayout>
  );
}

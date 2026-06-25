import { AuthForm } from "@/components/auth/auth-form";

export default function LoginPage() {
  return <main className="flex min-h-screen items-center justify-center bg-aurora px-6"><AuthForm mode="login" /></main>;
}
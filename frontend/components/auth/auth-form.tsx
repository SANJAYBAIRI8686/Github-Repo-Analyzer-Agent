"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { login, register } from "@/lib/api";
import { setSession } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type AuthFormProps = {
  mode: "login" | "register";
};

export function AuthForm({ mode }: AuthFormProps) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const response = mode === "login" ? await login(email, password) : await register(email, password);
      setSession(response.access_token, response.user);
      router.push("/dashboard");
    } catch (error_) {
      setError(error_ instanceof Error ? error_.message : "Unable to authenticate");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="w-full max-w-md">
      <form className="space-y-4" onSubmit={handleSubmit}>
        <div>
          <h1 className="text-2xl font-semibold text-white">{mode === "login" ? "Login" : "Register"}</h1>
          <p className="mt-1 text-sm text-slate-400">Secure access to repo ingestion and analysis.</p>
        </div>
        <Input value={email} onChange={(event) => setEmail(event.target.value)} placeholder="email@example.com" type="email" />
        <Input value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Password" type="password" />
        {error ? <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">{error}</div> : null}
        <Button className="w-full" disabled={loading} type="submit">
          {loading ? "Working..." : mode === "login" ? "Login" : "Create account"}
        </Button>
      </form>
    </Card>
  );
}
"use client";

import { Layers, LogIn } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ErrorBanner } from "@/components/ui/feedback";
import { api, ApiError } from "@/lib/api/client";
import { setSession } from "@/lib/session";

const inputCls =
  "h-9 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("admin");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await api.login(email, password);
      setSession(res.token, res.principal);
      router.replace("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-[80vh] items-center justify-center">
      <Card className="w-full max-w-sm p-6">
        <div className="mb-5 flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <Layers className="h-4 w-4" />
          </span>
          <div className="leading-tight">
            <div className="text-sm font-semibold">mmm-os</div>
            <div className="text-[11px] text-muted-foreground">Sign in to continue</div>
          </div>
        </div>

        <form onSubmit={onSubmit} className="space-y-3">
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Email</label>
            <input
              className={inputCls}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="username"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Password</label>
            <input
              type="password"
              className={inputCls}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>
          {error ? <ErrorBanner message={error} /> : null}
          <Button type="submit" className="w-full" disabled={busy}>
            <LogIn className="h-4 w-4" />
            {busy ? "Signing in…" : "Sign in"}
          </Button>
        </form>

        <p className="mt-4 text-center text-[11px] text-muted-foreground">
          Default dev login: <span className="mono">admin</span> /{" "}
          <span className="mono">admin123</span>
        </p>
      </Card>
    </div>
  );
}

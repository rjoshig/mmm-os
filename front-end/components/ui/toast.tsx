"use client";

import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";
import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";
import { cn } from "@/lib/utils";

type ToastKind = "success" | "error" | "info";

interface Toast {
  id: number;
  kind: ToastKind;
  message: string;
}

interface ToastApi {
  toast: (message: string, kind?: ToastKind) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

/** Access the toast API. Must be used under <ToastProvider>. */
export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within <ToastProvider>");
  return ctx;
}

const ICON: Record<ToastKind, typeof Info> = {
  success: CheckCircle2,
  error: AlertCircle,
  info: Info,
};

const TONE: Record<ToastKind, string> = {
  success: "border-success/40 text-success",
  error: "border-destructive/40 text-destructive",
  info: "border-border text-foreground",
};

/** App-wide toast provider + fixed viewport. Auto-dismisses after ~4s. */
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const seq = useRef(0);

  const dismiss = useCallback((id: number) => {
    setToasts((ts) => ts.filter((t) => t.id !== id));
  }, []);

  const push = useCallback(
    (message: string, kind: ToastKind) => {
      const id = (seq.current += 1);
      setToasts((ts) => [...ts, { id, kind, message }]);
      setTimeout(() => dismiss(id), 4000);
    },
    [dismiss]
  );

  const api = useMemo<ToastApi>(
    () => ({
      toast: (m, kind = "info") => push(m, kind),
      success: (m) => push(m, "success"),
      error: (m) => push(m, "error"),
      info: (m) => push(m, "info"),
    }),
    [push]
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-full max-w-sm flex-col gap-2">
        {toasts.map((t) => {
          const Icon = ICON[t.kind];
          return (
            <div
              key={t.id}
              role="status"
              className={cn(
                "pointer-events-auto flex items-start gap-2 rounded-lg border bg-card px-3 py-2.5 text-sm shadow-lg",
                TONE[t.kind]
              )}
            >
              <Icon className="mt-0.5 h-4 w-4 shrink-0" />
              <span className="min-w-0 flex-1 break-words text-card-foreground">{t.message}</span>
              <button
                type="button"
                onClick={() => dismiss(t.id)}
                className="shrink-0 text-muted-foreground hover:text-foreground"
                aria-label="Dismiss"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

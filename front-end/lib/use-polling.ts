"use client";

// Lightweight polling hook for live monitoring (Cycle 5, Phase 20).
// Calls `fn` every `intervalMs` while `enabled` is true; cleans up on unmount.

import { useEffect, useRef } from "react";

export function usePolling(fn: () => void, intervalMs: number, enabled: boolean): void {
  const saved = useRef(fn);
  useEffect(() => {
    saved.current = fn;
  }, [fn]);

  useEffect(() => {
    if (!enabled) return;
    const id = setInterval(() => saved.current(), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs, enabled]);
}

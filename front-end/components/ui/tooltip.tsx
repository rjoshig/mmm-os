"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

/**
 * Lightweight, dependency-free tooltip. Wraps a focusable trigger and shows
 * ``content`` on hover/focus. Token-styled (uses the popover tokens), a11y via
 * ``role="tooltip"``. Renders children untouched when there is no content.
 */
export function Tooltip({
  content,
  children,
  side = "top",
  className,
}: {
  content: React.ReactNode;
  children: React.ReactNode;
  side?: "top" | "bottom";
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  if (!content) return <>{children}</>;
  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      {children}
      {open ? (
        <span
          role="tooltip"
          className={cn(
            "pointer-events-none absolute left-1/2 z-50 w-max max-w-xs -translate-x-1/2 rounded-md border border-border bg-popover px-2 py-1 text-xs font-normal leading-snug text-popover-foreground shadow-md",
            side === "top" ? "bottom-full mb-1.5" : "top-full mt-1.5",
            className
          )}
        >
          {content}
        </span>
      ) : null}
    </span>
  );
}

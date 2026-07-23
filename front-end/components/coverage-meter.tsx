"use client";

import { cn } from "@/lib/utils";

/**
 * Live required-field coverage meter for the mapping screen.
 * Shows how many required canonical fields are satisfied by the current mapping
 * and lists any still missing. Pure derived UI — no API calls.
 */
export function CoverageMeter({
  required,
  coveredCount,
  missing,
}: {
  required: string[];
  coveredCount: number;
  missing: string[];
}) {
  const total = required.length;
  const pct = total > 0 ? Math.round((coveredCount / total) * 100) : 100;
  const complete = missing.length === 0;

  return (
    <div className="rounded-md border border-border bg-card px-3 py-2">
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium">Required fields covered</span>
        <span
          className={cn(
            "tabular-nums",
            complete ? "text-success" : "text-destructive"
          )}
        >
          {coveredCount}/{total}
        </span>
      </div>
      <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={cn("h-full rounded-full", complete ? "bg-success" : "bg-destructive")}
          style={{ width: `${pct}%` }}
        />
      </div>
      {!complete ? (
        <div className="mt-1.5 flex flex-wrap gap-1 text-[11px] text-muted-foreground">
          <span>missing:</span>
          {missing.map((m) => (
            <span key={m} className="rounded bg-destructive/10 px-1.5 py-0.5 text-destructive">
              {m}
            </span>
          ))}
        </div>
      ) : (
        <div className="mt-1.5 text-[11px] text-success">All required fields covered.</div>
      )}
    </div>
  );
}

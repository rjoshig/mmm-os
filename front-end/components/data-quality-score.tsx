"use client";

import { ShieldAlert, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import type { FlagRead } from "@/lib/api/types";

const SEVERITY_WEIGHT: Record<string, number> = { blocking: 3, warning: 1, info: 0.25 };
const CLEARED = new Set(["resolved", "overridden"]);

export interface QualitySummary {
  /** 0–100 severity-weighted share of flags cleared (100 when there are no flags). */
  score: number;
  total: number;
  cleared: number;
  openBlocking: number;
  openWarning: number;
  openInfo: number;
}

/** Derive the headline data-quality summary from a job's flags. */
export function computeQuality(flags: FlagRead[]): QualitySummary {
  let weightedTotal = 0;
  let weightedCleared = 0;
  let cleared = 0;
  let openBlocking = 0;
  let openWarning = 0;
  let openInfo = 0;

  for (const f of flags) {
    const sev = f.severity.toLowerCase();
    const w = SEVERITY_WEIGHT[sev] ?? 1;
    weightedTotal += w;
    const isCleared = CLEARED.has(f.review_status.toLowerCase());
    if (isCleared) {
      weightedCleared += w;
      cleared += 1;
    } else if (sev === "blocking") openBlocking += 1;
    else if (sev === "warning") openWarning += 1;
    else openInfo += 1;
  }

  const score =
    flags.length === 0 ? 100 : Math.round((100 * weightedCleared) / (weightedTotal || 1));
  return { score, total: flags.length, cleared, openBlocking, openWarning, openInfo };
}

function tone(score: number): { text: string; ring: string } {
  if (score >= 90) return { text: "text-success", ring: "border-success/40" };
  if (score >= 70) return { text: "text-tertiary-foreground", ring: "border-tertiary/50" };
  return { text: "text-destructive", ring: "border-destructive/40" };
}

/** Headline data-quality score + open-issue breakdown for the validation screen. */
export function DataQualityScore({ flags }: { flags: FlagRead[] }) {
  const q = computeQuality(flags);
  const t = tone(q.score);
  const clean = q.openBlocking === 0 && q.openWarning === 0 && q.openInfo === 0;

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-x-6 gap-y-3 rounded-lg border bg-card p-4",
        t.ring
      )}
    >
      <div className="flex items-center gap-3">
        {clean ? (
          <ShieldCheck className={cn("h-8 w-8", t.text)} />
        ) : (
          <ShieldAlert className={cn("h-8 w-8", t.text)} />
        )}
        <div>
          <div className={cn("text-3xl font-semibold tabular-nums leading-none", t.text)}>
            {q.score}
            <span className="text-lg">%</span>
          </div>
          <div className="mt-1 text-xs text-muted-foreground">Data quality</div>
        </div>
      </div>

      <div className="text-sm text-muted-foreground">
        {q.total === 0 ? (
          "No flags — nothing to review."
        ) : (
          <>
            {q.cleared} of {q.total} flags cleared. Severity-weighted; resolving or overriding
            flags raises the score.
          </>
        )}
      </div>

      {q.total > 0 ? (
        <div className="ml-auto flex items-center gap-2 text-xs">
          <Pill label="blocking" count={q.openBlocking} className="border-destructive/40 text-destructive" />
          <Pill label="warning" count={q.openWarning} className="border-tertiary/50 text-tertiary-foreground" />
          <Pill label="info" count={q.openInfo} className="border-border text-muted-foreground" />
        </div>
      ) : null}
    </div>
  );
}

function Pill({ label, count, className }: { label: string; count: number; className: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 tabular-nums",
        count === 0 ? "border-border text-muted-foreground opacity-60" : className
      )}
    >
      <span className="font-medium">{count}</span> {label} open
    </span>
  );
}

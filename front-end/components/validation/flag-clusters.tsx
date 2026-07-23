"use client";

import { ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";
import { Badge, statusVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { FlagRead } from "@/lib/api/types";

const CLEARED = new Set(["resolved", "overridden"]);
const SEVERITY_RANK: Record<string, number> = { blocking: 3, warning: 2, info: 1 };

const REVIEW_ACTIONS: { status: string; label: string }[] = [
  { status: "acknowledged", label: "Acknowledge" },
  { status: "resolved", label: "Resolve" },
  { status: "overridden", label: "Override" },
];

// Friendly names for the known validation checks (see src/mmm_os/validation).
const CHECK_LABEL: Record<string, string> = {
  missing_required: "Missing required value",
  type_mismatch: "Wrong data type",
  type_mismatch_required: "Wrong data type (required field)",
  duplicate_row: "Duplicate rows",
  date_gap: "Gaps in the date series",
  negative_measure: "Negative measure value",
  anomaly: "Anomalous value",
};

interface Cluster {
  key: string;
  check: string;
  field: string | null;
  severity: string;
  flags: FlagRead[];
  openIds: string[];
}

function locStr(loc: Record<string, unknown>, key: string): string | null {
  const v = loc[key];
  return v == null ? null : String(v);
}

function buildClusters(flags: FlagRead[]): Cluster[] {
  const byKey = new Map<string, Cluster>();
  for (const f of flags) {
    const check = locStr(f.location, "check") ?? "other";
    const field = locStr(f.location, "field");
    const key = `${check}::${field ?? ""}`;
    let cluster = byKey.get(key);
    if (!cluster) {
      cluster = { key, check, field, severity: f.severity, flags: [], openIds: [] };
      byKey.set(key, cluster);
    }
    cluster.flags.push(f);
    if ((SEVERITY_RANK[f.severity.toLowerCase()] ?? 0) > (SEVERITY_RANK[cluster.severity.toLowerCase()] ?? 0)) {
      cluster.severity = f.severity;
    }
    if (!CLEARED.has(f.review_status.toLowerCase())) cluster.openIds.push(f.id);
  }
  // Most severe, most numerous clusters first.
  return Array.from(byKey.values()).sort(
    (a, b) =>
      (SEVERITY_RANK[b.severity.toLowerCase()] ?? 0) - (SEVERITY_RANK[a.severity.toLowerCase()] ?? 0) ||
      b.flags.length - a.flags.length
  );
}

function clusterTitle(c: Cluster): string {
  const label = CHECK_LABEL[c.check] ?? c.check.replace(/_/g, " ");
  return c.field ? `${label} in “${c.field}”` : label;
}

/** Groups a job's flags into clusters (check + field) with bulk + per-row review. */
export function FlagClusters({
  flags,
  onBulkReview,
  onReview,
}: {
  flags: FlagRead[];
  onBulkReview: (flagIds: string[], status: string) => void;
  onReview: (flagId: string, status: string) => void;
}) {
  const clusters = buildClusters(flags);
  return (
    <div className="space-y-3">
      {clusters.map((c) => (
        <ClusterCard key={c.key} cluster={c} onBulkReview={onBulkReview} onReview={onReview} />
      ))}
    </div>
  );
}

function ClusterCard({
  cluster,
  onBulkReview,
  onReview,
}: {
  cluster: Cluster;
  onBulkReview: (flagIds: string[], status: string) => void;
  onReview: (flagId: string, status: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const total = cluster.flags.length;
  const openCount = cluster.openIds.length;
  const resolved = total - openCount;
  const allCleared = openCount === 0;

  return (
    <div className={cn("rounded-lg border bg-card", allCleared ? "border-border" : "border-border")}>
      <div className="flex flex-wrap items-center gap-3 p-4">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="text-muted-foreground hover:text-foreground"
          aria-label={open ? "Collapse" : "Expand"}
        >
          {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </button>
        <Badge variant={statusVariant(cluster.severity)}>{cluster.severity}</Badge>
        <div className="min-w-0">
          <div className="truncate text-sm font-medium">{clusterTitle(cluster)}</div>
          <div className="text-xs text-muted-foreground tabular-nums">
            {total} row{total === 1 ? "" : "s"}
            {resolved > 0 ? ` · ${resolved} cleared` : ""}
            {allCleared ? " · all cleared" : ` · ${openCount} open`}
          </div>
        </div>

        <div className="ml-auto flex items-center gap-1">
          {REVIEW_ACTIONS.map((a) => (
            <Button
              key={a.status}
              variant={a.status === "resolved" ? "outline" : "ghost"}
              size="sm"
              disabled={allCleared}
              onClick={() => onBulkReview(cluster.openIds, a.status)}
              title={`${a.label} all ${openCount} open in this group`}
            >
              {a.label} all
            </Button>
          ))}
        </div>
      </div>

      {open ? (
        <div className="border-t border-border">
          {cluster.flags.map((f) => (
            <div
              key={f.id}
              className="flex flex-wrap items-center gap-3 px-4 py-2 text-sm last:rounded-b-lg odd:bg-muted/30"
            >
              <span className="font-mono text-xs text-muted-foreground">
                {formatLocation(f.location)}
              </span>
              <span className="min-w-0 truncate text-muted-foreground">{f.description}</span>
              <Badge variant={statusVariant(f.review_status)}>{f.review_status}</Badge>
              <div className="ml-auto flex gap-1">
                {REVIEW_ACTIONS.map((a) => (
                  <Button
                    key={a.status}
                    variant="ghost"
                    size="sm"
                    disabled={f.review_status === a.status}
                    onClick={() => onReview(f.id, a.status)}
                  >
                    {a.label}
                  </Button>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function formatLocation(loc: Record<string, unknown>): string {
  const parts: string[] = [];
  if (loc.field != null) parts.push(`field=${String(loc.field)}`);
  if (loc.row != null) parts.push(`row=${String(loc.row)}`);
  if (loc.column != null) parts.push(`col=${String(loc.column)}`);
  return parts.length ? parts.join(" ") : "—";
}

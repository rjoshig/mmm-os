"use client";

import { ListChecks } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Badge, statusVariant } from "@/components/ui/badge";
import { DataTable, type DataColumn } from "@/components/ui/data-table";
import { ErrorBanner } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
import { TableSkeleton } from "@/components/ui/skeleton";
import { api, ApiError } from "@/lib/api/client";
import type { JobDetail, JobListItem, SyncRunListItem } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { usePolling } from "@/lib/use-polling";

type Tab = "jobs" | "syncs";

const ACTIVE = new Set(["pending", "running"]);

/** Human duration between two ISO timestamps, or "—" when unavailable. */
function duration(start?: string | null, end?: string | null): string {
  if (!start || !end) return "—";
  const ms = new Date(end).getTime() - new Date(start).getTime();
  if (!Number.isFinite(ms) || ms < 0) return "—";
  if (ms < 1000) return `${ms} ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)}s`;
  const m = Math.floor(s / 60);
  return `${m}m ${Math.round(s % 60)}s`;
}

export default function RunsPage() {
  const [tab, setTab] = useState<Tab>("jobs");
  const [jobs, setJobs] = useState<JobListItem[] | null>(null);
  const [syncs, setSyncs] = useState<SyncRunListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [j, s] = await Promise.all([api.listJobs(), api.listAllSyncRuns()]);
      setJobs(j);
      setSyncs(s);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load runs.");
      setJobs([]);
      setSyncs([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // Live monitoring: auto-refresh while any job is in flight, stop when idle.
  const activeCount = (jobs ?? []).filter((j) => ACTIVE.has(j.job.status)).length;
  usePolling(() => void load(), 4000, activeCount > 0);

  const jobColumns: DataColumn<JobListItem>[] = [
    {
      key: "status",
      header: "Status",
      cell: (r) => <Badge variant={statusVariant(r.job.status)}>{r.job.status}</Badge>,
      sortKey: (r) => r.job.status,
    },
    {
      key: "source",
      header: "Source",
      cell: (r) =>
        r.job.file_id ? (
          <Link
            href={`/files/${r.job.file_id}`}
            className="font-medium text-foreground hover:text-primary hover:underline"
          >
            {r.filename ?? "file"}
          </Link>
        ) : (
          <span className="text-muted-foreground">{r.filename ?? "—"}</span>
        ),
      sortKey: (r) => r.filename ?? "",
    },
    {
      key: "by",
      header: "Triggered by",
      cell: (r) => (
        <span className="text-muted-foreground">{r.triggered_by_email ?? "system"}</span>
      ),
      sortKey: (r) => r.triggered_by_email ?? "system",
    },
    {
      key: "started",
      header: "Started",
      cell: (r) => (
        <span className="text-muted-foreground">
          {formatDateTime(r.job.started_at ?? r.job.created_at)}
        </span>
      ),
      sortKey: (r) => r.job.started_at ?? r.job.created_at,
    },
    {
      key: "duration",
      header: "Duration",
      align: "right",
      cell: (r) => duration(r.job.started_at, r.job.finished_at),
      sortKey: (r) =>
        r.job.started_at && r.job.finished_at
          ? new Date(r.job.finished_at).getTime() - new Date(r.job.started_at).getTime()
          : -1,
    },
  ];

  const syncColumns: DataColumn<SyncRunListItem>[] = [
    {
      key: "status",
      header: "Status",
      cell: (r) => <Badge variant={statusVariant(r.run.status)}>{r.run.status}</Badge>,
      sortKey: (r) => r.run.status,
    },
    {
      key: "connector",
      header: "Connector",
      cell: (r) => (
        <span className="flex items-center gap-2">
          <span className="font-medium">{r.connector_name}</span>
          <Badge variant="secondary">{r.connector_key}</Badge>
        </span>
      ),
      sortKey: (r) => r.connector_name,
    },
    {
      key: "window",
      header: "Window",
      cell: (r) => (
        <span className="font-mono text-xs text-muted-foreground">
          {r.run.window_start} → {r.run.window_end}
        </span>
      ),
    },
    {
      key: "rows",
      header: "Rows",
      align: "right",
      cell: (r) => r.run.row_count ?? 0,
      sortKey: (r) => r.run.row_count ?? 0,
    },
    {
      key: "by",
      header: "Triggered by",
      cell: (r) => (
        <span className="text-muted-foreground">{r.triggered_by_email ?? "scheduler"}</span>
      ),
      sortKey: (r) => r.triggered_by_email ?? "scheduler",
    },
    {
      key: "finished",
      header: "Finished",
      cell: (r) => (
        <span className="text-muted-foreground">
          {formatDateTime(r.run.finished_at ?? r.run.started_at ?? "")}
        </span>
      ),
      sortKey: (r) => r.run.finished_at ?? r.run.started_at ?? "",
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Automation"
        title="Runs"
        description="Every pipeline job and connector sync — status, timing, who ran it, and per-stage logs (CC-7)."
        actions={
          activeCount > 0 ? (
            <span className="inline-flex items-center gap-1.5 rounded-md bg-success/12 px-2.5 py-1 text-xs font-medium text-success">
              <span className="h-2 w-2 animate-pulse rounded-full bg-success" />
              Live · {activeCount} running
            </span>
          ) : undefined
        }
      />

      <div className="inline-flex rounded-md border border-border p-0.5 text-sm">
        {(["jobs", "syncs"] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={
              tab === t
                ? "rounded px-3 py-1 bg-primary text-primary-foreground"
                : "rounded px-3 py-1 text-muted-foreground hover:text-foreground"
            }
          >
            {t === "jobs" ? "Pipeline jobs" : "Connector syncs"}
            {t === "jobs" && jobs ? ` (${jobs.length})` : ""}
            {t === "syncs" && syncs ? ` (${syncs.length})` : ""}
          </button>
        ))}
      </div>

      {error ? <ErrorBanner message={error} /> : null}

      {tab === "jobs" ? (
        jobs === null ? (
          <TableSkeleton rows={6} cols={5} />
        ) : (
          <DataTable
            rows={jobs}
            columns={jobColumns}
            rowKey={(r) => r.job.id}
            search={(r) => `${r.filename ?? ""} ${r.job.status} ${r.triggered_by_email ?? ""}`}
            searchPlaceholder="Search jobs…"
            emptyTitle="No jobs yet"
            emptyDescription="Process a file or run the pipeline to see jobs here."
            initialSort={{ key: "started", dir: "desc" }}
            expandable={(r) => <JobStages jobId={r.job.id} />}
          />
        )
      ) : null}

      {tab === "syncs" ? (
        syncs === null ? (
          <TableSkeleton rows={6} cols={5} />
        ) : (
          <DataTable
            rows={syncs}
            columns={syncColumns}
            rowKey={(r) => r.run.id}
            search={(r) => `${r.connector_name} ${r.connector_key} ${r.run.status}`}
            searchPlaceholder="Search syncs…"
            emptyTitle="No connector syncs yet"
            emptyDescription="Trigger a sync from Sources to see connector runs here."
            initialSort={{ key: "finished", dir: "desc" }}
          />
        )
      ) : null}
    </div>
  );
}

function JobStages({ jobId }: { jobId: string }) {
  const [detail, setDetail] = useState<JobDetail | null>(null);

  useEffect(() => {
    api
      .getJob(jobId)
      .then(setDetail)
      .catch(() => setDetail(null));
  }, [jobId]);

  if (detail === null) return <p className="text-xs text-muted-foreground">Loading stages…</p>;
  if (detail.job.error)
    return <p className="text-sm text-destructive">Error: {detail.job.error}</p>;
  if (detail.events.length === 0)
    return <p className="text-xs text-muted-foreground">No stage events recorded.</p>;

  return (
    <div className="space-y-1.5">
      {detail.events.map((ev, i) => (
        <div key={i} className="flex flex-wrap items-center gap-3 text-sm">
          <Badge variant={statusVariant(ev.status)}>{ev.status}</Badge>
          <span className="font-medium">{ev.stage}</span>
          {ev.message ? <span className="text-muted-foreground">{ev.message}</span> : null}
          {ev.duration_ms != null ? (
            <span className="ml-auto tabular-nums text-xs text-muted-foreground">
              {ev.duration_ms} ms
            </span>
          ) : null}
        </div>
      ))}
    </div>
  );
}

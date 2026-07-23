"use client";

import { ChevronDown, ChevronRight, ListChecks } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Badge, statusVariant } from "@/components/ui/badge";
import { EmptyState, ErrorBanner } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
import { TableSkeleton } from "@/components/ui/skeleton";
import { api, ApiError } from "@/lib/api/client";
import type { JobDetail, JobRead, SyncRunListItem } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";

type Tab = "jobs" | "syncs";

export default function RunsPage() {
  const [tab, setTab] = useState<Tab>("jobs");
  const [jobs, setJobs] = useState<JobRead[] | null>(null);
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

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Automation"
        title="Runs"
        description="Every pipeline job and connector sync, with status, timing, and stage logs (CC-7)."
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
          <TableSkeleton rows={5} cols={4} />
        ) : jobs.length === 0 ? (
          <EmptyState
            icon={<ListChecks className="h-6 w-6" />}
            title="No jobs yet"
            description="Process a file or run the pipeline to see jobs here."
          />
        ) : (
          <div className="space-y-2">
            {jobs.map((job) => (
              <JobRow key={job.id} job={job} />
            ))}
          </div>
        )
      ) : null}

      {tab === "syncs" ? (
        syncs === null ? (
          <TableSkeleton rows={5} cols={4} />
        ) : syncs.length === 0 ? (
          <EmptyState
            icon={<ListChecks className="h-6 w-6" />}
            title="No connector syncs yet"
            description="Trigger a sync from Sources to see connector runs here."
          />
        ) : (
          <div className="space-y-1.5">
            {syncs.map(({ run, connector_key, connector_name }) => (
              <div
                key={run.id}
                className="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-card px-4 py-2.5 text-sm"
              >
                <Badge variant={statusVariant(run.status)}>{run.status}</Badge>
                <span className="font-medium">{connector_name}</span>
                <Badge variant="secondary">{connector_key}</Badge>
                <span className="font-mono text-xs text-muted-foreground">
                  {run.window_start} → {run.window_end}
                </span>
                <span className="tabular-nums text-muted-foreground">{run.row_count ?? 0} rows</span>
                {run.error ? <span className="text-xs text-destructive">{run.error}</span> : null}
                <span className="ml-auto text-xs text-muted-foreground">
                  {formatDateTime(run.finished_at ?? run.started_at ?? "")}
                </span>
              </div>
            ))}
          </div>
        )
      ) : null}
    </div>
  );
}

function JobRow({ job }: { job: JobRead }) {
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState<JobDetail | null>(null);

  useEffect(() => {
    if (open && detail === null) {
      api.getJob(job.id).then(setDetail).catch(() => setDetail(null));
    }
  }, [open, detail, job.id]);

  return (
    <div className="rounded-lg border border-border bg-card">
      <div className="flex flex-wrap items-center gap-3 p-3">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="text-muted-foreground hover:text-foreground"
          aria-label={open ? "Collapse" : "Expand"}
        >
          {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </button>
        <Badge variant={statusVariant(job.status)}>{job.status}</Badge>
        <span className="text-sm">{detail?.filename ?? "job"}</span>
        {job.error ? <span className="text-xs text-destructive">{job.error}</span> : null}
        <div className="ml-auto flex items-center gap-3 text-xs text-muted-foreground">
          {job.file_id ? (
            <Link href={`/files/${job.file_id}`} className="hover:text-primary hover:underline">
              open file
            </Link>
          ) : null}
          <span>{formatDateTime(job.finished_at ?? job.created_at)}</span>
        </div>
      </div>

      {open ? (
        <div className="border-t border-border p-3">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Stages
          </h3>
          {detail === null ? (
            <p className="text-xs text-muted-foreground">Loading…</p>
          ) : detail.events.length === 0 ? (
            <p className="text-xs text-muted-foreground">No stage events recorded.</p>
          ) : (
            <div className="space-y-1.5">
              {detail.events.map((ev, i) => (
                <div key={i} className="flex flex-wrap items-center gap-3 text-sm">
                  <Badge variant={statusVariant(ev.status)}>{ev.status}</Badge>
                  <span className="font-medium">{ev.stage}</span>
                  {ev.message ? (
                    <span className="text-muted-foreground">{ev.message}</span>
                  ) : null}
                  {ev.duration_ms != null ? (
                    <span className="ml-auto tabular-nums text-xs text-muted-foreground">
                      {ev.duration_ms} ms
                    </span>
                  ) : null}
                </div>
              ))}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}

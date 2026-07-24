"use client";

import {
  Activity,
  AlertTriangle,
  FileSpreadsheet,
  GitBranch,
  Layers,
  Plug,
  Plus,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { AddSourceWizard } from "@/components/onboarding/add-source-wizard";
import { Badge, statusVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MiniBars, token, type BarDatum } from "@/components/ui/chart";
import { DataTable, type DataColumn } from "@/components/ui/data-table";
import { EmptyState, ErrorBanner } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
import { TableSkeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/ui/stat-card";
import { api, ApiError } from "@/lib/api/client";
import type {
  ConfigLibraryItem,
  DashboardResponse,
  FileListItem,
  JobListItem,
  SyncRunListItem,
} from "@/lib/api/types";
import { formatBytes, formatDateTime } from "@/lib/format";

const SEVERITY_COLOR: Record<string, string> = {
  blocking: token("destructive"),
  warning: token("tertiary"),
  info: token("muted-foreground"),
};

function KpiPanel({ kpi }: { kpi: DashboardResponse }) {
  const jobs: BarDatum[] = Object.entries(kpi.jobs_by_status).map(([label, value]) => ({
    label,
    value,
    color: label === "failed" ? token("destructive") : token("primary"),
  }));
  const flags: BarDatum[] = Object.entries(kpi.open_flags_by_severity).map(([label, value]) => ({
    label,
    value,
    color: SEVERITY_COLOR[label] ?? token("primary"),
  }));
  const syncs: BarDatum[] = Object.entries(kpi.sync_by_status).map(([label, value]) => ({
    label,
    value,
    color: label === "failed" ? token("destructive") : token("success"),
  }));
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card>
        <CardHeader>
          <CardTitle>Jobs by status</CardTitle>
        </CardHeader>
        <CardContent>
          {jobs.length ? <MiniBars data={jobs} /> : <Empty />}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Open flags by severity</CardTitle>
        </CardHeader>
        <CardContent>{flags.length ? <MiniBars data={flags} /> : <Empty />}</CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Connector sync health</CardTitle>
        </CardHeader>
        <CardContent>{syncs.length ? <MiniBars data={syncs} /> : <Empty />}</CardContent>
      </Card>
    </div>
  );
}

function Empty() {
  return <p className="text-sm text-muted-foreground">Nothing yet.</p>;
}

type Tab = "files" | "activity";

interface ActivityItem {
  id: string;
  at: string;
  icon: typeof FileSpreadsheet;
  status?: string;
  text: React.ReactNode;
}

export default function DashboardPage() {
  const [files, setFiles] = useState<FileListItem[] | null>(null);
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [configs, setConfigs] = useState<ConfigLibraryItem[]>([]);
  const [syncs, setSyncs] = useState<SyncRunListItem[]>([]);
  const [kpi, setKpi] = useState<DashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [tab, setTab] = useState<Tab>("files");

  const load = useCallback(async () => {
    try {
      const [f, j, c] = await Promise.all([
        api.listFiles(),
        api.listJobs().catch(() => []),
        api.getConfigLibrary().then((r) => r.items).catch(() => []),
      ]);
      setFiles(f);
      setJobs(j);
      setConfigs(c);
      setError(null);
      // Sync runs are admin-gated; tolerate a 403 for non-admins.
      api
        .listAllSyncRuns()
        .then(setSyncs)
        .catch(() => setSyncs([]));
      api
        .getDashboard()
        .then(setKpi)
        .catch(() => setKpi(null));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load dashboard.");
      setFiles([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const list = files ?? [];
  const needsAttention = list.filter(
    (i) => i.needs_review_sheets > 0 || i.latest_job_status === "failed"
  ).length;
  const failedJobs = jobs.filter((j) => j.job.status === "failed").length;

  const activity: ActivityItem[] = [
    ...jobs.map((j) => ({
      id: `job-${j.job.id}`,
      at: j.job.finished_at ?? j.job.created_at,
      icon: FileSpreadsheet,
      status: j.job.status,
      text: (
        <>
          Pipeline job {j.job.status} on{" "}
          {j.job.file_id ? (
            <Link href={`/files/${j.job.file_id}`} className="hover:text-primary hover:underline">
              {j.filename ?? "file"}
            </Link>
          ) : (
            j.filename ?? "file"
          )}
          {j.triggered_by_email ? ` · ${j.triggered_by_email}` : ""}
        </>
      ),
    })),
    ...syncs.map((s) => ({
      id: `sync-${s.run.id}`,
      at: s.run.finished_at ?? s.run.started_at ?? "",
      icon: Plug,
      status: s.run.status,
      text: (
        <>
          {s.connector_name} sync {s.run.status} · {s.run.row_count ?? 0} rows
          {s.triggered_by_email ? ` · ${s.triggered_by_email}` : ""}
        </>
      ),
    })),
    ...configs.map((c) => ({
      id: `cfg-${c.kind}-${c.key}`,
      at: c.updated_at,
      icon: GitBranch,
      status: c.status,
      text: (
        <>
          {c.name} ({c.kind === "mapping" ? "mapping" : "rule set"}) updated to v
          {c.latest_version}
          {c.created_by_email ? ` · ${c.created_by_email}` : ""}
        </>
      ),
    })),
  ]
    .filter((a) => a.at)
    .sort((a, b) => (a.at < b.at ? 1 : -1))
    .slice(0, 20);

  const fileColumns: DataColumn<FileListItem>[] = [
    {
      key: "file",
      header: "File",
      cell: (i) => (
        <Link
          href={`/files/${i.file.id}`}
          className="font-medium text-foreground hover:text-primary hover:underline"
        >
          {i.file.filename}
        </Link>
      ),
      sortKey: (i) => i.file.filename,
    },
    {
      key: "status",
      header: "Status",
      cell: (i) => (
        <Badge variant={statusVariant(i.latest_job_status)}>
          {i.latest_job_status ?? "pending"}
        </Badge>
      ),
      sortKey: (i) => i.latest_job_status ?? "",
    },
    { key: "sheets", header: "Sheets", align: "right", cell: (i) => i.sheet_count, sortKey: (i) => i.sheet_count },
    {
      key: "review",
      header: "Needs review",
      align: "right",
      cell: (i) =>
        i.needs_review_sheets > 0 ? (
          <Badge variant="warning">{i.needs_review_sheets}</Badge>
        ) : (
          <span className="text-muted-foreground">0</span>
        ),
      sortKey: (i) => i.needs_review_sheets,
    },
    {
      key: "size",
      header: "Size",
      align: "right",
      cell: (i) => <span className="text-muted-foreground">{formatBytes(i.file.byte_size)}</span>,
      sortKey: (i) => i.file.byte_size ?? 0,
    },
    {
      key: "uploaded",
      header: "Uploaded",
      cell: (i) => <span className="text-muted-foreground">{formatDateTime(i.file.created_at)}</span>,
      sortKey: (i) => i.file.created_at,
    },
  ];

  return (
    <div className="space-y-6">
      <AddSourceWizard open={wizardOpen} onClose={() => setWizardOpen(false)} onCompleted={load} />
      <PageHeader
        eyebrow="Review UI"
        title="Dashboard"
        description="Upload marketing data files, then map, transform, and validate them into clean, model-ready output."
        actions={
          <Button onClick={() => setWizardOpen(true)}>
            <Plus className="h-4 w-4" />
            Add source
          </Button>
        }
      />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Needs attention"
          value={needsAttention}
          icon={<AlertTriangle className="h-4 w-4 text-tertiary-foreground" />}
          hint="Files with sheets to review or a failed job"
        />
        <StatCard
          label="Failed jobs"
          value={failedJobs}
          icon={<XCircle className="h-4 w-4 text-destructive" />}
          hint="Pipeline jobs that failed and need a re-run"
        />
        <StatCard
          label="Files"
          value={files?.length ?? "—"}
          icon={<FileSpreadsheet className="h-4 w-4 text-muted-foreground" />}
        />
        <StatCard
          label="Stacks published"
          value={kpi ? `${kpi.stacks_published}/${kpi.stacks_total}` : "—"}
          icon={<Layers className="h-4 w-4 text-muted-foreground" />}
          hint="Model-ready panels published vs. total"
        />
      </div>

      {kpi ? <KpiPanel kpi={kpi} /> : null}

      {error ? <ErrorBanner message={error} /> : null}

      <div className="inline-flex rounded-md border border-border p-0.5 text-sm">
        {(["files", "activity"] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={
              tab === t
                ? "flex items-center gap-1.5 rounded px-3 py-1 bg-primary text-primary-foreground"
                : "flex items-center gap-1.5 rounded px-3 py-1 text-muted-foreground hover:text-foreground"
            }
          >
            {t === "files" ? <FileSpreadsheet className="h-3.5 w-3.5" /> : <Activity className="h-3.5 w-3.5" />}
            {t === "files" ? "Files" : "Recent activity"}
          </button>
        ))}
      </div>

      {tab === "files" ? (
        files === null ? (
          <TableSkeleton rows={5} cols={6} />
        ) : files.length === 0 ? (
          <EmptyState
            icon={<FileSpreadsheet className="h-6 w-6" />}
            title="No sources yet"
            description="Add a CSV or XLSX to start the ingest → map → transform → validate flow."
            action={
              <Button onClick={() => setWizardOpen(true)}>
                <Plus className="h-4 w-4" /> Add source
              </Button>
            }
          />
        ) : (
          <DataTable
            rows={files}
            columns={fileColumns}
            rowKey={(i) => i.file.id}
            search={(i) => `${i.file.filename} ${i.latest_job_status ?? ""}`}
            searchPlaceholder="Search files…"
            initialSort={{ key: "uploaded", dir: "desc" }}
          />
        )
      ) : null}

      {tab === "activity" ? (
        files === null ? (
          <TableSkeleton rows={5} cols={2} />
        ) : activity.length === 0 ? (
          <EmptyState
            icon={<Activity className="h-6 w-6" />}
            title="No recent activity"
            description="Runs, syncs, and config changes will show up here as your team works."
          />
        ) : (
          <div className="space-y-1.5">
            {activity.map((a) => {
              const Icon = a.icon;
              return (
                <div
                  key={a.id}
                  className="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-card px-4 py-2.5 text-sm"
                >
                  <Icon className="h-4 w-4 text-muted-foreground" />
                  {a.status ? <Badge variant={statusVariant(a.status)}>{a.status}</Badge> : null}
                  <span className="min-w-0">{a.text}</span>
                  <span className="ml-auto text-xs text-muted-foreground">
                    {formatDateTime(a.at)}
                  </span>
                </div>
              );
            })}
          </div>
        )
      ) : null}
    </div>
  );
}

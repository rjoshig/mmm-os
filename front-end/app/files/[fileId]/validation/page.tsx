"use client";

import {
  ArrowLeft,
  ArrowRight,
  Download,
  FileDown,
  FileSpreadsheet,
  GitBranch,
  HardDriveUpload,
  Play,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { DataQualityScore } from "@/components/data-quality-score";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MiniBars, SimpleBarChart, token, type BarDatum } from "@/components/ui/chart";
import { EmptyState, ErrorBanner, Loading } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
import { Table, TD, TH, THead, TR } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { FlagClusters } from "@/components/validation/flag-clusters";
import { api, ApiError } from "@/lib/api/client";
import type {
  FileDetail,
  FlagRead,
  GenerateOutputResponse,
  OutputContract,
  OutputLineage,
  OutputRowRead,
  OutputStatsResponse,
} from "@/lib/api/types";

export default function ValidationReviewPage() {
  const { fileId } = useParams<{ fileId: string }>();
  const toast = useToast();
  const [file, setFile] = useState<FileDetail | null>(null);
  const [flags, setFlags] = useState<FlagRead[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [outputSummary, setOutputSummary] = useState<GenerateOutputResponse | null>(null);
  const [outputRows, setOutputRows] = useState<OutputRowRead[] | null>(null);

  const jobId = file?.latest_job?.id ?? null;
  const firstSheetId = file?.sheets[0]?.id ?? null;

  const load = useCallback(async () => {
    try {
      const detail = await api.getFile(fileId);
      setFile(detail);
      if (detail.latest_job) {
        setFlags(await api.getFlags(detail.latest_job.id));
      } else {
        setFlags([]);
      }
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load validation.");
      setFlags([]);
    }
  }, [fileId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function onRun() {
    if (!jobId || !file) return;
    setRunning(true);
    setError(null);
    try {
      // Validates the first sheet's data after applying its saved mapping + rule
      // set server-side — not raw, un-mapped columns.
      const first = file.sheets[0];
      if (!first) return;
      const res = await api.validateSheet(jobId, first.id);
      setFlags(res.flags);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Validation run failed.");
    } finally {
      setRunning(false);
    }
  }

  async function onReview(flagId: string, status: string) {
    try {
      const updated = await api.reviewFlag(flagId, status);
      setFlags((fs) => (fs ?? []).map((f) => (f.id === flagId ? updated : f)));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Review failed.");
    }
  }

  async function onSuggestFixes() {
    const firstSheet = file?.sheets[0];
    if (!firstSheet) return;
    try {
      const res = await api.suggestTransforms(firstSheet.id, true);
      if (res.suggestions.length) {
        toast.success(
          `${res.suggestions.length} AI fix(es) proposed — open the transform builder to apply.`
        );
      } else {
        toast.info("No AI fixes proposed for the current issues.");
      }
    } catch (err) {
      const msg =
        err instanceof ApiError && err.isLlmDisabled
          ? "AI is disabled — set LLM_ENABLED on the backend."
          : err instanceof ApiError
            ? err.message
            : "Could not get AI fixes.";
      toast.error(msg);
    }
  }

  async function onBulkReview(flagIds: string[], status: string) {
    if (!jobId || flagIds.length === 0) return;
    try {
      const { updated } = await api.bulkReviewFlags(jobId, flagIds, status);
      const byId = new Map(updated.map((f) => [f.id, f]));
      setFlags((fs) => (fs ?? []).map((f) => byId.get(f.id) ?? f));
      toast.success(`${status.replace(/^\w/, (c) => c.toUpperCase())} ${updated.length} flag(s).`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Bulk review failed.");
      toast.error("Bulk review failed.");
    }
  }

  async function onGenerate(force = false) {
    if (!jobId || !firstSheetId) return;
    setGenerating(true);
    setError(null);
    try {
      const summary = await api.generateOutput(jobId, firstSheetId, force);
      setOutputSummary(summary);
      const out = await api.getOutput(jobId, 50);
      setOutputRows(out.rows);
      toast.success(`Generated ${summary.rows_written} clean output row(s).`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Output generation failed.");
      toast.error("Output generation failed.");
    } finally {
      setGenerating(false);
    }
  }

  const blocked = (flags ?? []).some(
    (f) =>
      f.severity.toLowerCase() === "blocking" &&
      f.review_status !== "resolved" &&
      f.review_status !== "overridden"
  );

  return (
    <div className="space-y-6">
      <Link
        href={`/files/${fileId}`}
        className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Back to file
      </Link>

      <PageHeader
        eyebrow="Validation review"
        title={file?.file.filename ?? "Validation"}
        description="Review quality flags with severity, location, and explanation; acknowledge, resolve, or override."
        actions={
          jobId ? (
            <div className="flex items-center gap-2">
              {(flags ?? []).length > 0 ? (
                <Button variant="outline" onClick={onSuggestFixes}>
                  <Sparkles className="h-4 w-4" />
                  Suggest fixes (AI)
                </Button>
              ) : null}
              <Button variant="outline" onClick={onRun} disabled={running}>
                <Play className="h-4 w-4" />
                {running ? "Running…" : "Run validation"}
              </Button>
              <Button
                onClick={() => onGenerate(false)}
                disabled={generating || !firstSheetId || blocked}
                title={blocked ? "Resolve/override blocking flags first, or force" : undefined}
              >
                <Download className="h-4 w-4" />
                {generating ? "Generating…" : "Generate output"}
              </Button>
            </div>
          ) : undefined
        }
      />

      {blocked ? (
        <div className="flex items-center gap-2 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          <ShieldAlert className="h-4 w-4" />
          <span>Output is blocked by unresolved blocking-severity flags.</span>
          <button
            type="button"
            className="ml-auto text-xs underline underline-offset-2"
            onClick={() => onGenerate(true)}
            disabled={generating || !firstSheetId}
          >
            {generating ? "Forcing…" : "Generate anyway (force)"}
          </button>
        </div>
      ) : null}
      {outputSummary ? (
        <div className="rounded-md border border-success/30 bg-success/10 px-3 py-2 text-sm text-success">
          Generated {outputSummary.rows_written} clean output rows · mapping v
          {outputSummary.mapping_config_version ?? "—"} · rules v
          {outputSummary.rule_set_version ?? "—"}.
        </div>
      ) : null}
      {outputSummary && jobId ? <ExportToMmm jobId={jobId} /> : null}
      {outputSummary && jobId ? <OutputLineagePanel jobId={jobId} /> : null}
      {error ? <ErrorBanner message={error} /> : null}

      {flags === null ? (
        <Loading label="Loading flags…" />
      ) : flags.length === 0 ? (
        <EmptyState
          icon={<ShieldCheck className="h-6 w-6" />}
          title="No validation flags"
          description={
            jobId
              ? "Run validation to check this file's data against the quality policy."
              : "Process this file first to create a job to validate."
          }
        />
      ) : (
        <div className="space-y-4">
          <DataQualityScore flags={flags} />
          <FailureDistribution flags={flags} />
          <div>
            <h2 className="mb-2 text-sm font-semibold">
              Issues grouped by type ({flags.length} flag{flags.length === 1 ? "" : "s"})
            </h2>
            <p className="mb-3 text-xs text-muted-foreground">
              Similar flags are clustered so you can resolve a whole group at once. Expand a group
              to review individual rows.
            </p>
            <FlagClusters flags={flags} onBulkReview={onBulkReview} onReview={onReview} />
          </div>
        </div>
      )}

      {outputSummary && jobId ? <OutputStatsPanel jobId={jobId} /> : null}

      {outputRows ? (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold">Clean output ({outputRows.length} shown)</h2>
          {outputRows.length === 0 ? (
            <EmptyState
              title="No output rows"
              description="Generate output to finalize this file's clean, canonical data."
            />
          ) : (
            <OutputPreview rows={outputRows} />
          )}
        </div>
      ) : null}
    </div>
  );
}

const SEVERITY_TONE: Record<string, string> = {
  blocking: token("destructive"),
  warning: token("tertiary"),
  info: token("muted-foreground"),
};

/** Distribution of failing rows per check — the meaningful-validation view (Phase 17). */
function FailureDistribution({ flags }: { flags: FlagRead[] }) {
  const counts = new Map<string, { count: number; severity: string }>();
  for (const f of flags) {
    const check = String((f.location as { check?: string }).check ?? "other");
    const prev = counts.get(check);
    counts.set(check, { count: (prev?.count ?? 0) + 1, severity: f.severity });
  }
  const data: BarDatum[] = [...counts.entries()]
    .map(([label, { count, severity }]) => ({
      label,
      value: count,
      color: SEVERITY_TONE[severity.toLowerCase()] ?? token("primary"),
    }))
    .sort((a, b) => b.value - a.value);
  if (data.length === 0) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Failures by check</CardTitle>
      </CardHeader>
      <CardContent>
        <MiniBars data={data} />
      </CardContent>
    </Card>
  );
}

/** Per-measure output statistics (min/max/mean/…) once output is generated (Phase 17). */
function OutputStatsPanel({ jobId }: { jobId: string }) {
  const [stats, setStats] = useState<OutputStatsResponse | null>(null);
  useEffect(() => {
    api
      .getOutputStats(jobId)
      .then(setStats)
      .catch(() => setStats(null));
  }, [jobId]);
  if (!stats || stats.measures.length === 0) return null;
  const meanData: BarDatum[] = stats.measures
    .filter((m) => m.mean != null)
    .map((m) => ({ label: m.measure, value: Number(m.mean) }));
  return (
    <Card>
      <CardHeader>
        <CardTitle>Output statistics · {stats.row_count.toLocaleString()} rows</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {meanData.length > 0 && <SimpleBarChart data={meanData} valueLabel="mean" height={180} />}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted-foreground">
                <th className="py-2 pr-4">Measure</th>
                <th className="py-2 pr-4 text-right">Min</th>
                <th className="py-2 pr-4 text-right">Max</th>
                <th className="py-2 pr-4 text-right">Mean</th>
                <th className="py-2 pr-4 text-right">Null %</th>
              </tr>
            </thead>
            <tbody className="tabular-nums">
              {stats.measures.map((m) => (
                <tr key={m.measure} className="border-b border-border/60">
                  <td className="py-2 pr-4 font-medium">{m.measure}</td>
                  <td className="py-2 pr-4 text-right">{m.min ?? "—"}</td>
                  <td className="py-2 pr-4 text-right">{m.max ?? "—"}</td>
                  <td className="py-2 pr-4 text-right">{m.mean ?? "—"}</td>
                  <td className="py-2 pr-4 text-right">{Math.round(m.null_rate * 100)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

function OutputPreview({ rows }: { rows: OutputRowRead[] }) {
  const cols = Array.from(new Set(rows.flatMap((r) => Object.keys(r.data))));
  return (
    <Table>
      <THead>
        <TR>
          {cols.map((c) => (
            <TH key={c}>{c}</TH>
          ))}
        </TR>
      </THead>
      <tbody>
        {rows.slice(0, 20).map((r) => (
          <TR key={r.id}>
            {cols.map((c) => (
              <TD key={c} className="tabular-nums">
                {r.data[c] == null ? (
                  <span className="text-muted-foreground">—</span>
                ) : (
                  String(r.data[c])
                )}
              </TD>
            ))}
          </TR>
        ))}
      </tbody>
    </Table>
  );
}

const KIND_TONE: Record<string, string> = {
  dimension: "border-border text-muted-foreground",
  measure: "border-primary/40 text-primary",
  factor: "border-tertiary/50 text-tertiary-foreground",
};

function ExportToMmm({ jobId }: { jobId: string }) {
  const toast = useToast();
  const [contract, setContract] = useState<OutputContract | null>(null);
  const [open, setOpen] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [writing, setWriting] = useState(false);

  async function writeToDestination() {
    setWriting(true);
    try {
      const res = await api.exportToDestination(jobId);
      toast.success(
        res.written_key
          ? `Wrote ${res.row_count} rows to ${res.written_key}.`
          : "No output rows to write."
      );
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not write to destination.");
    } finally {
      setWriting(false);
    }
  }

  async function toggleContract() {
    const next = !open;
    setOpen(next);
    if (next && contract === null) {
      try {
        setContract(await api.getOutputContract(jobId));
      } catch (err) {
        toast.error(err instanceof ApiError ? err.message : "Could not load contract.");
      }
    }
  }

  async function downloadCsv() {
    setDownloading(true);
    try {
      const blob = await api.fetchOutputCsv(jobId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${contract?.filename?.replace(/\.[^.]+$/, "") ?? "output"}_mmm.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("CSV downloaded.");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "CSV export failed.");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="min-w-0">
          <div className="text-sm font-semibold">Export to MMM</div>
          <div className="text-xs text-muted-foreground">
            Model-ready clean output — download as CSV or inspect the schema contract.
          </div>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={toggleContract}>
            {open ? "Hide contract" : "View contract"}
          </Button>
          <Button variant="outline" size="sm" onClick={writeToDestination} disabled={writing}>
            <HardDriveUpload className="h-4 w-4" />
            {writing ? "Writing…" : "Write to destination"}
          </Button>
          <Button size="sm" onClick={downloadCsv} disabled={downloading}>
            <FileDown className="h-4 w-4" />
            {downloading ? "Preparing…" : "Download CSV"}
          </Button>
        </div>
      </div>

      {open && contract ? (
        <div className="mt-4 space-y-3 border-t border-border pt-3">
          <div className="text-xs text-muted-foreground">
            {contract.row_count} rows · mapping v{contract.mapping_config_version ?? "—"} · rules v
            {contract.rule_set_version ?? "—"} · {contract.columns.length} columns
          </div>
          <div className="flex flex-wrap gap-1.5">
            {contract.columns.map((col) => (
              <span
                key={col.name}
                className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs ${
                  KIND_TONE[col.kind] ?? "border-border"
                }`}
              >
                <span className="font-medium">{col.name}</span>
                <span className="opacity-70">
                  {col.type}·{col.kind}
                </span>
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Node({
  icon,
  title,
  subtitle,
}: {
  icon: React.ReactNode;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="flex min-w-[7rem] flex-col items-center rounded-lg border border-border bg-background px-3 py-2 text-center">
      <div className="text-muted-foreground">{icon}</div>
      <div className="mt-1 max-w-[9rem] truncate text-xs font-medium">{title}</div>
      <div className="text-[0.7rem] text-muted-foreground">{subtitle}</div>
    </div>
  );
}

function Arrow() {
  return <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground" />;
}

/** Renders the stored source → config → output provenance for a job's output (CC-3). */
function OutputLineagePanel({ jobId }: { jobId: string }) {
  const [lineage, setLineage] = useState<OutputLineage | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getOutputLineage(jobId)
      .then(setLineage)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load lineage."));
  }, [jobId]);

  if (error) return null;
  if (!lineage) return null;

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="mb-3 flex items-center gap-2">
        <GitBranch className="h-4 w-4 text-muted-foreground" />
        <div className="text-sm font-semibold">Lineage</div>
        <span className="text-xs text-muted-foreground">
          every clean row traces back to its source (CC-3)
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Node
          icon={<FileSpreadsheet className="h-4 w-4" />}
          title={lineage.filename}
          subtitle="source file"
        />
        <Arrow />
        <div className="flex flex-wrap items-center gap-1.5">
          {lineage.sources.map((s, i) => (
            <Node
              key={i}
              icon={<FileSpreadsheet className="h-4 w-4" />}
              title={s.source_sheet ?? "—"}
              subtitle={`${s.row_count} rows`}
            />
          ))}
        </div>
        <Arrow />
        <Node
          icon={<GitBranch className="h-4 w-4" />}
          title={`mapping v${lineage.mapping_config_version ?? "—"}`}
          subtitle={`rules v${lineage.rule_set_version ?? "—"}`}
        />
        <Arrow />
        <Node
          icon={<Download className="h-4 w-4" />}
          title={`${lineage.output_row_count} rows`}
          subtitle="clean output"
        />
      </div>
    </div>
  );
}

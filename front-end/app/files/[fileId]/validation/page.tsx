"use client";

import { ArrowLeft, Download, Play, ShieldAlert, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Badge, statusVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorBanner, Loading } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
import { Table, TD, TH, THead, TR } from "@/components/ui/table";
import { api, ApiError } from "@/lib/api/client";
import type {
  FileDetail,
  FlagRead,
  GenerateOutputResponse,
  OutputRowRead,
} from "@/lib/api/types";

const REVIEW_ACTIONS: { status: string; label: string }[] = [
  { status: "acknowledged", label: "Acknowledge" },
  { status: "resolved", label: "Resolve" },
  { status: "overridden", label: "Override" },
];

export default function ValidationReviewPage() {
  const { fileId } = useParams<{ fileId: string }>();
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

  async function onGenerate(force = false) {
    if (!jobId || !firstSheetId) return;
    setGenerating(true);
    setError(null);
    try {
      const summary = await api.generateOutput(jobId, firstSheetId, force);
      setOutputSummary(summary);
      const out = await api.getOutput(jobId, 50);
      setOutputRows(out.rows);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Output generation failed.");
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
        <Table>
          <THead>
            <TR>
              <TH>Severity</TH>
              <TH>Issue</TH>
              <TH>Location</TH>
              <TH>Status</TH>
              <TH className="text-right">Review</TH>
            </TR>
          </THead>
          <tbody>
            {flags.map((f) => (
              <TR key={f.id}>
                <TD>
                  <Badge variant={statusVariant(f.severity)}>{f.severity}</Badge>
                </TD>
                <TD className="max-w-md">{f.description}</TD>
                <TD className="font-mono text-xs text-muted-foreground">
                  {formatLocation(f.location)}
                </TD>
                <TD>
                  <Badge variant={statusVariant(f.review_status)}>{f.review_status}</Badge>
                </TD>
                <TD>
                  <div className="flex justify-end gap-1">
                    {REVIEW_ACTIONS.map((a) => (
                      <Button
                        key={a.status}
                        variant="ghost"
                        size="sm"
                        onClick={() => onReview(f.id, a.status)}
                        disabled={f.review_status === a.status}
                      >
                        {a.label}
                      </Button>
                    ))}
                  </div>
                </TD>
              </TR>
            ))}
          </tbody>
        </Table>
      )}

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

function formatLocation(loc: Record<string, unknown>): string {
  const parts: string[] = [];
  if (loc.field != null) parts.push(`field=${String(loc.field)}`);
  if (loc.row != null) parts.push(`row=${String(loc.row)}`);
  if (loc.column != null) parts.push(`col=${String(loc.column)}`);
  return parts.length ? parts.join(" ") : "—";
}

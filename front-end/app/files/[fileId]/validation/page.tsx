"use client";

import { ArrowLeft, Play, ShieldAlert, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Badge, statusVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorBanner, Loading } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
import { Table, TD, TH, THead, TR } from "@/components/ui/table";
import { api, ApiError } from "@/lib/api/client";
import type { FileDetail, FlagRead } from "@/lib/api/types";
import { sampleRowsFromProfile } from "@/lib/sample";

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

  const jobId = file?.latest_job?.id ?? null;

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
      // Best-effort: validate the first sheet's profiled sample rows (interim —
      // the backend has no stored-rows endpoint yet; see phase-06 notes).
      const first = file.sheets[0];
      const rows = first ? sampleRowsFromProfile(await api.getSheet(first.id), 50) : [];
      const res = await api.validateJob(jobId, rows);
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

  const blocked = (flags ?? []).some(
    (f) => f.severity.toLowerCase() === "block" && f.review_status === "open"
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
            <Button variant="outline" onClick={onRun} disabled={running}>
              <Play className="h-4 w-4" />
              {running ? "Running…" : "Run validation"}
            </Button>
          ) : undefined
        }
      />

      {blocked ? (
        <div className="flex items-center gap-2 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          <ShieldAlert className="h-4 w-4" />
          Output is blocked by unresolved BLOCK-severity flags.
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

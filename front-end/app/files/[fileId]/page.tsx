"use client";

import { ArrowLeft, Play, ShieldCheck, Table2, UserPlus, Wand2 } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Badge, statusVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState, ErrorBanner, Loading } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
import { PipelineStepper } from "@/components/pipeline-stepper";
import { Table, TD, TH, THead, TR } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api/client";
import type {
  FileDetail,
  FilePipelineStatus,
  PipelineRunResponse,
  UserRead,
} from "@/lib/api/types";
import { formatBytes, formatDateTime } from "@/lib/format";

export default function FileDetailPage() {
  const params = useParams<{ fileId: string }>();
  const fileId = params.fileId;
  const [data, setData] = useState<FileDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [pipeline, setPipeline] = useState<PipelineRunResponse | null>(null);
  const [status, setStatus] = useState<FilePipelineStatus | null>(null);

  const load = useCallback(async () => {
    try {
      const [detail, st] = await Promise.all([
        api.getFile(fileId),
        api.getPipelineStatus(fileId).catch(() => null),
      ]);
      setData(detail);
      setStatus(st);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load file.");
    }
  }, [fileId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function onRunPipeline() {
    setRunning(true);
    setError(null);
    setPipeline(null);
    try {
      const res = await api.runPipeline(fileId);
      setPipeline(res);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Pipeline run failed.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-6">
      <Link
        href="/"
        className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Dashboard
      </Link>

      {error ? <ErrorBanner message={error} /> : null}

      {data === null ? (
        <Loading label="Loading file…" />
      ) : (
        <>
          <PageHeader
            eyebrow="File"
            title={data.file.filename}
            description={`${formatBytes(data.file.byte_size)} · uploaded ${formatDateTime(
              data.file.created_at
            )}`}
            actions={
              <div className="flex items-center gap-2">
                <AssignForReview fileId={params.fileId} />
                <Button onClick={onRunPipeline} disabled={running || data.sheets.length === 0}>
                  <Play className="h-4 w-4" />
                  {running ? "Running pipeline…" : "Run pipeline"}
                </Button>
                <Badge variant={statusVariant(data.latest_job?.status)}>
                  {data.latest_job?.status ?? "pending"}
                </Badge>
              </div>
            }
          />

          {pipeline ? (
            <div className="rounded-md border border-success/30 bg-success/10 px-3 py-2 text-sm text-success">
              Pipeline complete: {pipeline.rows_written} clean output row(s).
              {pipeline.sheets.map((s) => (
                <span key={s.sheet_id} className="ml-2">
                  · {s.sheet_name ?? "sheet"}:{" "}
                  {s.needs_mapping
                    ? "needs mapping"
                    : s.blocked
                      ? `${s.flag_count} flag(s), blocked`
                      : `${s.output_rows_written} rows`}
                </span>
              ))}
            </div>
          ) : null}

          {data.latest_job ? (
            <Link href={`/files/${fileId}/validation`}>
              <Button variant="outline" size="sm">
                <ShieldCheck className="h-4 w-4" /> Validation review
              </Button>
            </Link>
          ) : null}

          {data.sheets.length === 0 ? (
            <EmptyState
              icon={<Table2 className="h-6 w-6" />}
              title="No sheets detected"
              description="Processing found no non-empty sheets, or the job failed."
            />
          ) : (
            <div className="space-y-3">
              {status ? (
                <div className="space-y-2">
                  {status.sheets.map((s) => (
                    <div
                      key={s.sheet_id}
                      className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border bg-card px-3 py-2"
                    >
                      <div className="text-xs font-medium text-muted-foreground">
                        {s.sheet_name ?? "Sheet"}
                      </div>
                      <PipelineStepper sheet={s} file={status} />
                    </div>
                  ))}
                </div>
              ) : null}
              <Table>
              <THead>
                <TR>
                  <TH>Sheet</TH>
                  <TH>Status</TH>
                  <TH>Header row</TH>
                  <TH>Columns</TH>
                  <TH className="text-right">Actions</TH>
                </TR>
              </THead>
              <tbody>
                {data.sheets.map((s) => (
                  <TR key={s.id} className="hover:bg-muted/40">
                    <TD className="font-medium">{s.sheet_name ?? `Sheet ${s.sheet_index + 1}`}</TD>
                    <TD>
                      <Badge variant={statusVariant(s.status)}>{s.status}</Badge>
                    </TD>
                    <TD className="tabular-nums text-muted-foreground">
                      {s.header_row_index != null ? s.header_row_index + 1 : "—"}
                    </TD>
                    <TD className="tabular-nums">{s.columns.length}</TD>
                    <TD>
                      <div className="flex justify-end gap-2">
                        <Link href={`/sheets/${s.id}/mapping`}>
                          <Button variant="outline" size="sm">
                            <Table2 className="h-3.5 w-3.5" /> Map
                          </Button>
                        </Link>
                        <Link href={`/sheets/${s.id}/transform`}>
                          <Button variant="ghost" size="sm">
                            <Wand2 className="h-3.5 w-3.5" /> Transform
                          </Button>
                        </Link>
                      </div>
                    </TD>
                  </TR>
                ))}
              </tbody>
            </Table>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function AssignForReview({ fileId }: { fileId: string }) {
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [users, setUsers] = useState<UserRead[]>([]);
  const [assignee, setAssignee] = useState("");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    api
      .listUsers()
      .then((u) => {
        setUsers(u);
        if (u[0]) setAssignee(u[0].id);
        setLoadError(null);
      })
      .catch((err) =>
        setLoadError(err instanceof ApiError ? err.message : "Could not load users.")
      );
  }, [open]);

  async function assign() {
    if (!assignee) return;
    setSaving(true);
    try {
      await api.createAssignment({
        target_type: "file",
        target_id: fileId,
        assignee_user_id: assignee,
        note: note.trim() || undefined,
      });
      toast.success("Assigned for review.");
      setOpen(false);
      setNote("");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not assign.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        title="Assign for review"
        description="Hand this file to a teammate — it lands in their review queue."
      >
        <div className="space-y-4">
          {loadError ? <ErrorBanner message={loadError} /> : null}
          <label className="block space-y-1.5">
            <span className="text-sm font-medium">Assignee</span>
            <select
              className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              value={assignee}
              onChange={(e) => setAssignee(e.target.value)}
            >
              {users.length === 0 ? <option value="">No users found</option> : null}
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.email}
                </option>
              ))}
            </select>
          </label>
          <label className="block space-y-1.5">
            <span className="text-sm font-medium">Note (optional)</span>
            <input
              className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              placeholder="please review the channel mapping"
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </label>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button onClick={assign} disabled={saving || !assignee}>
              {saving ? "Assigning…" : "Assign"}
            </Button>
          </div>
        </div>
      </Dialog>
      <Button variant="outline" onClick={() => setOpen(true)}>
        <UserPlus className="h-4 w-4" /> Assign
      </Button>
    </>
  );
}

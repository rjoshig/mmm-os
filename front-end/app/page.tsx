"use client";

import { AlertTriangle, FileSpreadsheet, Layers, Plus } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { AddSourceWizard } from "@/components/onboarding/add-source-wizard";
import { Badge, statusVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorBanner } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
import { TableSkeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/ui/stat-card";
import { Table, TD, TH, THead, TR } from "@/components/ui/table";
import { api, ApiError } from "@/lib/api/client";
import type { FileListItem } from "@/lib/api/types";
import { formatBytes, formatDateTime } from "@/lib/format";

export default function DashboardPage() {
  const [items, setItems] = useState<FileListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [wizardOpen, setWizardOpen] = useState(false);

  const load = useCallback(async () => {
    try {
      setItems(await api.listFiles());
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load files.");
      setItems([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const needsAttention = (items ?? []).filter(
    (i) => i.needs_review_sheets > 0 || i.latest_job_status === "failed"
  ).length;

  return (
    <div className="space-y-6">
      <AddSourceWizard
        open={wizardOpen}
        onClose={() => setWizardOpen(false)}
        onCompleted={load}
      />
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

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard
          label="Files"
          value={items?.length ?? "—"}
          icon={<FileSpreadsheet className="h-4 w-4 text-muted-foreground" />}
        />
        <StatCard
          label="Sheets"
          value={(items ?? []).reduce((n, i) => n + i.sheet_count, 0)}
          icon={<Layers className="h-4 w-4 text-muted-foreground" />}
        />
        <StatCard
          label="Needs attention"
          value={needsAttention}
          icon={<AlertTriangle className="h-4 w-4 text-muted-foreground" />}
          hint="Files with sheets to review or a failed job"
        />
      </div>

      {error ? <ErrorBanner message={error} /> : null}

      {items === null ? (
        <TableSkeleton rows={5} cols={6} />
      ) : items.length === 0 ? (
        <EmptyState
          icon={<FileSpreadsheet className="h-6 w-6" />}
          title="No sources yet"
          description="Add a CSV or XLSX to start the ingest → map → transform → validate flow."
          action={
            <Button onClick={() => setWizardOpen(true)}>
              <Plus className="h-4 w-4" />
              Add source
            </Button>
          }
        />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>File</TH>
              <TH>Status</TH>
              <TH>Sheets</TH>
              <TH>Needs review</TH>
              <TH>Size</TH>
              <TH>Uploaded</TH>
            </TR>
          </THead>
          <tbody>
            {items.map((i) => (
              <TR key={i.file.id} className="hover:bg-muted/40">
                <TD>
                  <Link
                    href={`/files/${i.file.id}`}
                    className="font-medium text-foreground hover:text-primary hover:underline"
                  >
                    {i.file.filename}
                  </Link>
                </TD>
                <TD>
                  <Badge variant={statusVariant(i.latest_job_status)}>
                    {i.latest_job_status ?? "pending"}
                  </Badge>
                </TD>
                <TD className="tabular-nums">{i.sheet_count}</TD>
                <TD className="tabular-nums">
                  {i.needs_review_sheets > 0 ? (
                    <Badge variant="warning">{i.needs_review_sheets}</Badge>
                  ) : (
                    <span className="text-muted-foreground">0</span>
                  )}
                </TD>
                <TD className="tabular-nums text-muted-foreground">
                  {formatBytes(i.file.byte_size)}
                </TD>
                <TD className="text-muted-foreground">{formatDateTime(i.file.created_at)}</TD>
              </TR>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}

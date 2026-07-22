"use client";

import { ArrowLeft, ShieldCheck, Table2, Wand2 } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Badge, statusVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorBanner, Loading } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
import { Table, TD, TH, THead, TR } from "@/components/ui/table";
import { api, ApiError } from "@/lib/api/client";
import type { FileDetail } from "@/lib/api/types";
import { formatBytes, formatDateTime } from "@/lib/format";

export default function FileDetailPage() {
  const params = useParams<{ fileId: string }>();
  const fileId = params.fileId;
  const [data, setData] = useState<FileDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setData(await api.getFile(fileId));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load file.");
    }
  }, [fileId]);

  useEffect(() => {
    void load();
  }, [load]);

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
              <Badge variant={statusVariant(data.latest_job?.status)}>
                {data.latest_job?.status ?? "pending"}
              </Badge>
            }
          />

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
          )}
        </>
      )}
    </div>
  );
}

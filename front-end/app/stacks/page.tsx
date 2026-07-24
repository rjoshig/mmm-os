"use client";

import { Boxes, Copy, Plus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { CloneDialog } from "@/components/clone-dialog";
import { AssembleStackWizard } from "@/components/stacks/assemble-stack-wizard";
import { Badge, statusVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataTable, type DataColumn } from "@/components/ui/data-table";
import { ErrorBanner } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
import { TableSkeleton } from "@/components/ui/skeleton";
import { api, ApiError } from "@/lib/api/client";
import type { StackRead } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";

export default function StacksPage() {
  const router = useRouter();
  const [stacks, setStacks] = useState<StackRead[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [cloneTarget, setCloneTarget] = useState<StackRead | null>(null);

  const load = useCallback(async () => {
    try {
      setStacks(await api.listStacks());
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load stacks.");
      setStacks([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const columns: DataColumn<StackRead>[] = [
    {
      key: "name",
      header: "Stack",
      cell: (s) => (
        <Link
          href={`/stacks/${s.id}`}
          className="font-medium text-foreground hover:text-primary hover:underline"
        >
          {s.name}
        </Link>
      ),
      sortKey: (s) => s.name,
    },
    {
      key: "status",
      header: "Status",
      cell: (s) => <Badge variant={statusVariant(s.lifecycle_status)}>{s.lifecycle_status}</Badge>,
      sortKey: (s) => s.lifecycle_status,
    },
    { key: "version", header: "Version", align: "right", cell: (s) => `v${s.version}` },
    { key: "grain", header: "Grain", cell: (s) => s.grain ?? "—" },
    {
      key: "sources",
      header: "Sources",
      align: "right",
      cell: (s) => s.source_job_ids.length,
      sortKey: (s) => s.source_job_ids.length,
    },
    {
      key: "created",
      header: "Created",
      cell: (s) => <span className="text-muted-foreground">{formatDateTime(s.created_at)}</span>,
      sortKey: (s) => s.created_at,
    },
    {
      key: "actions",
      header: "",
      align: "right",
      cell: (s) => (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setCloneTarget(s)}
          aria-label="Duplicate stack"
        >
          <Copy className="h-4 w-4" />
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Stage 2 · Harmonize"
        title="Stacks"
        description="Model-ready panels (Gold): assemble cleaned per-source outputs, harmonize across sources, validate, and publish for modelling."
        actions={
          <Button size="sm" onClick={() => setWizardOpen(true)}>
            <Plus className="h-4 w-4" /> Assemble stack
          </Button>
        }
      />

      {error ? <ErrorBanner message={error} /> : null}

      {stacks === null ? (
        <TableSkeleton rows={5} cols={6} />
      ) : (
        <DataTable
          rows={stacks}
          columns={columns}
          rowKey={(s) => s.id}
          search={(s) => `${s.name} ${s.lifecycle_status} ${s.grain ?? ""}`}
          searchPlaceholder="Search stacks…"
          emptyTitle="No stacks yet"
          emptyDescription="Assemble your first stack from cleaned pipeline outputs."
          initialSort={{ key: "created", dir: "desc" }}
        />
      )}

      <AssembleStackWizard
        open={wizardOpen}
        onClose={() => setWizardOpen(false)}
        onCreated={(id) => {
          setWizardOpen(false);
          router.push(`/stacks/${id}`);
        }}
      />

      {cloneTarget && (
        <CloneDialog
          open
          onClose={() => setCloneTarget(null)}
          entityLabel="stack"
          currentName={cloneTarget.name}
          onClone={async (opts) => {
            await api.cloneStack(cloneTarget.id, { new_name: opts.new_name });
            await load();
          }}
        />
      )}
    </div>
  );
}

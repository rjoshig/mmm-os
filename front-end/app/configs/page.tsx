"use client";

import { useCallback, useEffect, useState } from "react";
import { Badge, statusVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataTable, type DataColumn } from "@/components/ui/data-table";
import { ErrorBanner } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
import { TableSkeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api/client";
import type { ConfigLibraryItem, ConfigVersionItem } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";

export default function ConfigsPage() {
  const [items, setItems] = useState<ConfigLibraryItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0); // bump to force a reload after publish

  const load = useCallback(async () => {
    try {
      setItems((await api.getConfigLibrary()).items);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load config library.");
      setItems([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load, tick]);

  const columns: DataColumn<ConfigLibraryItem>[] = [
    {
      key: "kind",
      header: "Type",
      cell: (r) => (
        <Badge variant="secondary">{r.kind === "mapping" ? "mapping" : "rule set"}</Badge>
      ),
      sortKey: (r) => r.kind,
    },
    {
      key: "name",
      header: "Name",
      cell: (r) => <span className="font-medium">{r.name}</span>,
      sortKey: (r) => r.name,
    },
    {
      key: "version",
      header: "Version",
      cell: (r) => <VersionCell item={r} onPublished={() => setTick((t) => t + 1)} />,
    },
    {
      key: "author",
      header: "Author (latest)",
      cell: (r) => <span className="text-muted-foreground">{r.created_by_email ?? "system"}</span>,
      sortKey: (r) => r.created_by_email ?? "system",
    },
    {
      key: "updated",
      header: "Updated",
      cell: (r) => <span className="text-muted-foreground">{formatDateTime(r.updated_at)}</span>,
      sortKey: (r) => r.updated_at,
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Collaboration"
        title="Config library"
        description="Every saved mapping and rule set your team owns. Configs are shared: one person configures, another reuses. Pick a version to inspect its status and author."
      />

      {error ? <ErrorBanner message={error} /> : null}

      {items === null ? (
        <TableSkeleton rows={6} cols={5} />
      ) : (
        <DataTable
          rows={items}
          columns={columns}
          rowKey={(r) => `${r.kind}:${r.key}`}
          search={(r) => `${r.name} ${r.kind} ${r.status}`}
          searchPlaceholder="Search configs…"
          emptyTitle="No saved configs yet"
          emptyDescription="Map a sheet or save a transform rule set and it will appear here for the whole team."
          initialSort={{ key: "updated", dir: "desc" }}
        />
      )}
    </div>
  );
}

/**
 * A per-row version control: a dropdown defaulting to the latest version. Selecting
 * a version lazily fetches the family's history (cached) and shows that version's
 * status + summary; draft versions get a Publish action.
 */
function VersionCell({
  item,
  onPublished,
}: {
  item: ConfigLibraryItem;
  onPublished: () => void;
}) {
  const toast = useToast();
  const [versions, setVersions] = useState<ConfigVersionItem[] | null>(null);
  const [selected, setSelected] = useState<number>(item.latest_version);
  const [busy, setBusy] = useState(false);

  const ensureVersions = useCallback(async () => {
    if (versions !== null) return;
    try {
      setVersions((await api.getConfigVersions(item.kind, item.key)).versions);
    } catch {
      setVersions([]);
    }
  }, [versions, item.kind, item.key]);

  const current = versions?.find((v) => v.version === selected) ?? null;
  const status = current?.status ?? (selected === item.latest_version ? item.status : "—");

  async function publish() {
    setBusy(true);
    try {
      await api.publishConfig(item.kind, item.key, selected);
      toast.success(`Published v${selected}.`);
      onPublished();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Publish failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <select
        value={selected}
        onFocus={ensureVersions}
        onChange={(e) => setSelected(Number(e.target.value))}
        className="h-7 rounded-md border border-input bg-background px-1.5 text-xs tabular-nums focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        {(versions
          ? versions.map((v) => v.version)
          : Array.from({ length: item.latest_version }, (_, i) => item.latest_version - i)
        ).map((v) => (
          <option key={v} value={v}>
            v{v}
            {v === item.latest_version ? " (latest)" : ""}
          </option>
        ))}
      </select>
      <Badge variant={statusVariant(status)}>{status}</Badge>
      {current ? (
        <span className="text-xs text-muted-foreground">{current.summary}</span>
      ) : null}
      {status === "draft" ? (
        <Button variant="outline" size="sm" onClick={publish} disabled={busy}>
          {busy ? "…" : "Publish"}
        </Button>
      ) : null}
    </div>
  );
}

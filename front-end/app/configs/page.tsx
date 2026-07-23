"use client";

import { ChevronDown, ChevronRight, Library, User } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { EmptyState, ErrorBanner } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
import { TableSkeleton } from "@/components/ui/skeleton";
import { api, ApiError } from "@/lib/api/client";
import type { ConfigLibraryItem, ConfigVersionItem } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";

export default function ConfigsPage() {
  const [items, setItems] = useState<ConfigLibraryItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setItems((await api.getConfigLibrary()).items);
        setError(null);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load config library.");
        setItems([]);
      }
    })();
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Collaboration"
        title="Config library"
        description="Every saved mapping and rule set your team owns — with version history and who authored each version. Configs are shared: one person configures, another reuses."
      />

      {error ? <ErrorBanner message={error} /> : null}

      {items === null ? (
        <TableSkeleton rows={5} cols={4} />
      ) : items.length === 0 ? (
        <EmptyState
          icon={<Library className="h-6 w-6" />}
          title="No saved configs yet"
          description="Map a sheet or save a transform rule set and it will appear here for the whole team."
        />
      ) : (
        <div className="space-y-2">
          {items.map((item) => (
            <ConfigCard key={`${item.kind}:${item.key}`} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

function ConfigCard({ item }: { item: ConfigLibraryItem }) {
  const [open, setOpen] = useState(false);
  const [versions, setVersions] = useState<ConfigVersionItem[] | null>(null);

  const loadVersions = useCallback(async () => {
    try {
      setVersions((await api.getConfigVersions(item.kind, item.key)).versions);
    } catch {
      setVersions([]);
    }
  }, [item.kind, item.key]);

  useEffect(() => {
    if (open && versions === null) void loadVersions();
  }, [open, versions, loadVersions]);

  return (
    <div className="rounded-lg border border-border bg-card">
      <div className="flex flex-wrap items-center gap-3 p-4">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="text-muted-foreground hover:text-foreground"
          aria-label={open ? "Collapse" : "Expand"}
        >
          {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </button>
        <Badge variant="secondary">{item.kind === "mapping" ? "mapping" : "rule set"}</Badge>
        <div className="min-w-0">
          <div className="truncate text-sm font-medium">{item.name}</div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>
              v{item.latest_version} · {item.version_count} version
              {item.version_count === 1 ? "" : "s"}
            </span>
            <span className="inline-flex items-center gap-1">
              <User className="h-3 w-3" />
              {item.created_by_email ?? "system"}
            </span>
          </div>
        </div>
        <span className="ml-auto text-xs text-muted-foreground">
          {formatDateTime(item.updated_at)}
        </span>
      </div>

      {open ? (
        <div className="border-t border-border p-4">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Version history
          </h3>
          {versions === null ? (
            <p className="text-xs text-muted-foreground">Loading…</p>
          ) : (
            <div className="space-y-1.5">
              {versions.map((v) => (
                <div key={v.version} className="flex flex-wrap items-center gap-3 text-sm">
                  <Badge variant="secondary">v{v.version}</Badge>
                  <span className="text-muted-foreground">{v.summary}</span>
                  <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                    <User className="h-3 w-3" />
                    {v.created_by_email ?? "system"}
                  </span>
                  <span className="ml-auto text-xs text-muted-foreground">
                    {formatDateTime(v.created_at)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}

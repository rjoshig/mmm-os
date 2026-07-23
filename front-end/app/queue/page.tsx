"use client";

import { CheckCircle2, Inbox } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorBanner } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
import { TableSkeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api/client";
import type { Assignment } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";

export default function QueuePage() {
  const toast = useToast();
  const [items, setItems] = useState<Assignment[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setItems(await api.listAssignments());
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load the review queue.");
      setItems([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function resolve(id: string) {
    try {
      await api.resolveAssignment(id);
      toast.success("Marked done.");
      await load();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not resolve.");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Collaboration"
        title="Review queue"
        description="Work assigned across the team — hand a file or sheet to a teammate and track what's open."
      />

      {error ? <ErrorBanner message={error} /> : null}

      {items === null ? (
        <TableSkeleton rows={4} cols={4} />
      ) : items.length === 0 ? (
        <EmptyState
          icon={<Inbox className="h-6 w-6" />}
          title="Nothing in the queue"
          description="Assign a file or sheet for review from its detail page and it will show up here."
        />
      ) : (
        <div className="space-y-2">
          {items.map((a) => (
            <div
              key={a.id}
              className="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-card px-4 py-3 text-sm"
            >
              <Badge variant="secondary">{a.target_type}</Badge>
              {a.target_type === "file" ? (
                <Link
                  href={`/files/${a.target_id}`}
                  className="font-medium text-foreground hover:text-primary hover:underline"
                >
                  open {a.target_type}
                </Link>
              ) : (
                <span className="font-mono text-xs text-muted-foreground">{a.target_id}</span>
              )}
              <span className="text-muted-foreground">
                → {a.assignee_email ?? a.assignee_user_id}
              </span>
              {a.note ? <span className="text-xs text-muted-foreground">“{a.note}”</span> : null}
              <span className="ml-auto text-xs text-muted-foreground">
                {formatDateTime(a.created_at)}
              </span>
              <Button variant="outline" size="sm" onClick={() => resolve(a.id)}>
                <CheckCircle2 className="h-3.5 w-3.5" /> Done
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

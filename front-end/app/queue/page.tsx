"use client";

import { Bell, CheckCircle2, Inbox } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorBanner } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
import { TableSkeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api/client";
import type { Assignment, Notification } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";

export default function QueuePage() {
  const toast = useToast();
  const [items, setItems] = useState<Assignment[] | null>(null);
  const [notifications, setNotifications] = useState<Notification[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [assignments, notifs] = await Promise.all([
        api.listAssignments(),
        api.listNotifications(),
      ]);
      setItems(assignments);
      setNotifications(notifs);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load the review queue.");
      setItems([]);
      setNotifications([]);
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

  async function markRead(id: string) {
    try {
      await api.markNotificationRead(id);
      setNotifications((ns) =>
        (ns ?? []).map((n) => (n.id === id ? { ...n, read: true } : n))
      );
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not update notification.");
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

      <div>
        <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold">
          <Bell className="h-4 w-4 text-muted-foreground" /> Notifications
          {notifications ? (
            <span className="text-xs font-normal text-muted-foreground">
              ({notifications.filter((n) => !n.read).length} unread)
            </span>
          ) : null}
        </h2>
        {notifications === null ? (
          <TableSkeleton rows={2} cols={2} />
        ) : notifications.length === 0 ? (
          <p className="rounded-md border border-dashed border-border px-3 py-4 text-center text-xs text-muted-foreground">
            No notifications. Mentions, assignments, and publishes show up here.
          </p>
        ) : (
          <div className="space-y-1.5">
            {notifications.map((n) => (
              <div
                key={n.id}
                className={`flex flex-wrap items-center gap-3 rounded-lg border px-4 py-2.5 text-sm ${
                  n.read ? "border-border bg-card opacity-60" : "border-primary/30 bg-primary/5"
                }`}
              >
                <Badge variant="secondary">{n.kind}</Badge>
                <span>{n.message}</span>
                {n.target_type === "file" && n.target_id ? (
                  <Link
                    href={`/files/${n.target_id}`}
                    className="text-xs text-primary hover:underline"
                  >
                    open file
                  </Link>
                ) : null}
                <span className="ml-auto text-xs text-muted-foreground">
                  {formatDateTime(n.created_at)}
                </span>
                {!n.read ? (
                  <Button variant="ghost" size="sm" onClick={() => markRead(n.id)}>
                    Mark read
                  </Button>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

"use client";

import { Database, ScrollText, ShieldCheck, Users } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Badge, statusVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorBanner, Loading } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
import { Table, TD, TH, THead, TR } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api/client";
import type { AccessReviewRow, AuditEntryRead, RetentionPolicy, UserRead } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { getStoredPrincipal } from "@/lib/session";
import { cn } from "@/lib/utils";

type Tab = "users" | "audit" | "access" | "retention";

const TABS: { id: Tab; label: string; icon: typeof Users }[] = [
  { id: "users", label: "Users", icon: Users },
  { id: "audit", label: "Audit log", icon: ScrollText },
  { id: "access", label: "Access review", icon: ShieldCheck },
  { id: "retention", label: "Data retention", icon: Database },
];

/**
 * Admin console (Phase 8 / 08.1). Admin-gated in the sidebar and re-checked here;
 * the backend still enforces Permission.ADMIN on every call, so a non-admin who
 * reaches this route sees a permission notice rather than data.
 */
export default function AdminPage() {
  const principal = getStoredPrincipal();
  const [tab, setTab] = useState<Tab>("users");

  if (principal && principal.role !== "admin") {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Governance" title="Admin" />
        <EmptyState
          icon={<ShieldCheck className="h-6 w-6" />}
          title="Admin access required"
          description="Your account does not have the admin role for this tenant."
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Governance"
        title="Admin"
        description="Manage users, review the tenant audit trail, and run an access review (RBAC, Phase 8 / 08.1)."
      />

      <div className="flex gap-1 border-b border-border">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={cn(
              "-mb-px flex items-center gap-2 border-b-2 px-3 py-2 text-sm font-medium transition-colors",
              tab === id
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {tab === "users" ? <UsersTab /> : null}
      {tab === "audit" ? <AuditTab /> : null}
      {tab === "access" ? <AccessTab /> : null}
      {tab === "retention" ? <RetentionTab /> : null}
    </div>
  );
}

function RetentionTab() {
  const toast = useToast();
  const [policy, setPolicy] = useState<RetentionPolicy | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    api
      .getRetentionPolicy()
      .then(setPolicy)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load policy."));
  }, []);

  async function run() {
    setRunning(true);
    try {
      const { purged } = await api.runRetention();
      const total = Object.values(purged).reduce((a, b) => a + b, 0);
      toast.success(`Retention run complete — purged ${total} record(s).`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Retention run failed.");
    } finally {
      setRunning(false);
    }
  }

  const rows: { label: string; days: number | undefined }[] = [
    { label: "Raw files (+ derived data & storage bytes)", days: policy?.raw_file_days },
    { label: "LLM usage", days: policy?.llm_usage_days },
    { label: "Connector sync runs", days: policy?.sync_run_days },
    { label: "Read notifications", days: policy?.notification_days },
    { label: "Audit log", days: policy?.audit_log_days },
  ];

  return (
    <div className="space-y-4">
      {error ? <ErrorBanner message={error} /> : null}
      <div className="flex items-start justify-between gap-4">
        <p className="max-w-2xl text-sm text-muted-foreground">
          Data past its retention window is purged (idempotent). Purging a raw file cascades its
          derived data and immutable-raw bytes (the governance exception to immutability). Windows
          are configured via <span className="mono">RETENTION_*</span> env vars.
        </p>
        <Button onClick={run} disabled={running || policy === null}>
          <Database className="h-4 w-4" />
          {running ? "Purging…" : "Run retention now"}
        </Button>
      </div>
      {policy === null ? (
        <Loading label="Loading policy…" />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Data class</TH>
              <TH className="text-right">Retention</TH>
            </TR>
          </THead>
          <tbody>
            {rows.map((r) => (
              <TR key={r.label}>
                <TD>{r.label}</TD>
                <TD className="text-right tabular-nums">
                  {r.days === 0 ? (
                    <span className="text-muted-foreground">keep forever</span>
                  ) : (
                    `${r.days} days`
                  )}
                </TD>
              </TR>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}

/** Load helper: runs `fetcher`, tracking data + error the same way across tabs. */
function useAdminData<T>(fetcher: () => Promise<T>, fallback: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setData(await fetcher());
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : fallback);
    }
    // fetcher is a stable per-tab closure; intentionally not a dep.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fallback]);

  useEffect(() => {
    void load();
  }, [load]);

  return { data, error };
}

function UsersTab() {
  const { data, error } = useAdminData<UserRead[]>(() => api.listUsers(), "Failed to load users.");

  if (error) return <ErrorBanner message={error} />;
  if (data === null) return <Loading label="Loading users…" />;
  if (data.length === 0)
    return (
      <EmptyState
        icon={<Users className="h-6 w-6" />}
        title="No users"
        description="This tenant has no users yet."
      />
    );

  return (
    <Table>
      <THead>
        <TR>
          <TH>Email</TH>
          <TH>Name</TH>
          <TH>Role</TH>
          <TH>Status</TH>
        </TR>
      </THead>
      <tbody>
        {data.map((u) => (
          <TR key={u.id} className="hover:bg-muted/40">
            <TD className="font-medium text-foreground">{u.email}</TD>
            <TD className="text-muted-foreground">{u.display_name ?? "—"}</TD>
            <TD>
              <Badge variant={u.role === "admin" ? "default" : "secondary"}>{u.role}</Badge>
            </TD>
            <TD>
              <Badge variant={statusVariant(u.status)}>{u.status}</Badge>
            </TD>
          </TR>
        ))}
      </tbody>
    </Table>
  );
}

function AuditTab() {
  const { data, error } = useAdminData<AuditEntryRead[]>(
    () => api.auditLog(100),
    "Failed to load the audit log."
  );

  if (error) return <ErrorBanner message={error} />;
  if (data === null) return <Loading label="Loading audit log…" />;
  if (data.length === 0)
    return (
      <EmptyState
        icon={<ScrollText className="h-6 w-6" />}
        title="No audit entries"
        description="Admin and review actions are recorded here as they happen."
      />
    );

  return (
    <Table>
      <THead>
        <TR>
          <TH>When</TH>
          <TH>Action</TH>
          <TH>Target</TH>
          <TH>Actor</TH>
        </TR>
      </THead>
      <tbody>
        {data.map((e) => (
          <TR key={e.id} className="hover:bg-muted/40">
            <TD className="whitespace-nowrap text-muted-foreground">
              {formatDateTime(e.created_at)}
            </TD>
            <TD className="font-medium text-foreground">{e.action}</TD>
            <TD className="text-muted-foreground">
              {e.target_type ? `${e.target_type}${e.target_id ? `:${e.target_id}` : ""}` : "—"}
            </TD>
            <TD className="mono text-xs text-muted-foreground">{e.actor_user_id ?? "system"}</TD>
          </TR>
        ))}
      </tbody>
    </Table>
  );
}

function AccessTab() {
  const { data, error } = useAdminData<AccessReviewRow[]>(
    () => api.accessReview(),
    "Failed to run the access review."
  );

  if (error) return <ErrorBanner message={error} />;
  if (data === null) return <Loading label="Running access review…" />;
  if (data.length === 0)
    return (
      <EmptyState
        icon={<ShieldCheck className="h-6 w-6" />}
        title="Nothing to review"
        description="No users are provisioned for this tenant."
      />
    );

  return (
    <Table>
      <THead>
        <TR>
          <TH>Email</TH>
          <TH>Role</TH>
          <TH>Effective permissions</TH>
        </TR>
      </THead>
      <tbody>
        {data.map((r) => (
          <TR key={r.user_id} className="hover:bg-muted/40">
            <TD className="font-medium text-foreground">{r.email}</TD>
            <TD>
              <Badge variant={r.role === "admin" ? "default" : "secondary"}>{r.role}</Badge>
            </TD>
            <TD>
              <div className="flex flex-wrap gap-1">
                {r.permissions.length === 0 ? (
                  <span className="text-muted-foreground">none</span>
                ) : (
                  r.permissions.map((p) => (
                    <Badge key={p} variant="outline">
                      {p}
                    </Badge>
                  ))
                )}
              </div>
            </TD>
          </TR>
        ))}
      </tbody>
    </Table>
  );
}

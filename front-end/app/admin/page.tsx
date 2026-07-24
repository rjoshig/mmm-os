"use client";

import {
  Boxes,
  Database,
  KeyRound,
  ListChecks,
  Plus,
  ScrollText,
  ShieldCheck,
  Trash2,
  Users,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Badge, statusVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState, ErrorBanner, Loading } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
import { Table, TD, TH, THead, TR } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api/client";
import type {
  AccessReviewRow,
  AuditEntryRead,
  ResolvedField,
  RetentionPolicy,
  RoleMatrixResponse,
  SchemaExtension,
  UserRead,
  ValidationRule,
} from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { getStoredPrincipal } from "@/lib/session";
import { cn } from "@/lib/utils";

const inputCls =
  "h-9 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";
const ADMIN_ROLES = new Set(["admin", "platform_admin"]);

type Tab = "users" | "roles" | "schema" | "validation" | "audit" | "access" | "retention";

const TABS: { id: Tab; label: string; icon: typeof Users }[] = [
  { id: "users", label: "Users", icon: Users },
  { id: "roles", label: "Roles", icon: KeyRound },
  { id: "schema", label: "Schema & Fields", icon: Boxes },
  { id: "validation", label: "Validation rules", icon: ListChecks },
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

  if (principal && !ADMIN_ROLES.has(principal.role)) {
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
      {tab === "roles" ? <RolesTab /> : null}
      {tab === "schema" ? <SchemaTab /> : null}
      {tab === "validation" ? <ValidationRulesTab /> : null}
      {tab === "audit" ? <AuditTab /> : null}
      {tab === "access" ? <AccessTab /> : null}
      {tab === "retention" ? <RetentionTab /> : null}
    </div>
  );
}

/** Role management (Phase 19): assign roles + view the role→permission matrix. */
function RolesTab() {
  const toast = useToast();
  const [users, setUsers] = useState<UserRead[] | null>(null);
  const [matrix, setMatrix] = useState<RoleMatrixResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [u, m] = await Promise.all([api.listUsers(), api.getRoleMatrix()]);
      setUsers(u);
      setMatrix(m);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load roles.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function setRole(userId: string, role: string) {
    try {
      await api.setUserRole(userId, role);
      toast.success(`Role updated to ${role}.`);
      await load();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not set role.");
    }
  }

  if (error) return <ErrorBanner message={error} />;
  if (users === null || matrix === null) return <Loading label="Loading roles…" />;

  const roles = Object.keys(matrix.roles);

  return (
    <div className="space-y-6">
      <div>
        <h3 className="mb-2 text-sm font-semibold">Assign roles</h3>
        {users.length === 0 ? (
          <EmptyState icon={<Users className="h-6 w-6" />} title="No users" />
        ) : (
          <Table>
            <THead>
              <TR>
                <TH>Email</TH>
                <TH>Name</TH>
                <TH>Role</TH>
              </TR>
            </THead>
            <tbody>
              {users.map((u) => (
                <TR key={u.id} className="hover:bg-muted/40">
                  <TD className="font-medium text-foreground">{u.email}</TD>
                  <TD className="text-muted-foreground">{u.display_name ?? "—"}</TD>
                  <TD>
                    <select
                      className={cn(inputCls, "h-8 w-40")}
                      value={u.role}
                      onChange={(e) => setRole(u.id, e.target.value)}
                    >
                      {roles.map((r) => (
                        <option key={r} value={r}>
                          {r}
                        </option>
                      ))}
                    </select>
                  </TD>
                </TR>
              ))}
            </tbody>
          </Table>
        )}
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold">Role → permission matrix</h3>
        <Table>
          <THead>
            <TR>
              <TH>Role</TH>
              <TH>Permissions</TH>
            </TR>
          </THead>
          <tbody>
            {roles.map((role) => (
              <TR key={role}>
                <TD className="font-medium">{role}</TD>
                <TD>
                  <div className="flex flex-wrap gap-1">
                    {matrix.roles[role].map((p) => (
                      <Badge key={p} variant="outline">
                        {p}
                      </Badge>
                    ))}
                  </div>
                </TD>
              </TR>
            ))}
          </tbody>
        </Table>
      </div>
    </div>
  );
}

/** Tenant schema extensions (Phase 21): custom dimensions/measures/factors. */
function SchemaTab() {
  const toast = useToast();
  const [exts, setExts] = useState<SchemaExtension[] | null>(null);
  const [resolved, setResolved] = useState<ResolvedField[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState({
    kind: "dimension",
    name: "",
    data_type: "string",
  });

  const load = useCallback(async () => {
    try {
      const [e, r] = await Promise.all([api.listSchemaExtensions(), api.getResolvedSchema()]);
      setExts(e);
      setResolved(r.fields);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load schema.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function create() {
    try {
      await api.createSchemaExtension({
        kind: form.kind,
        name: form.name.trim(),
        data_type: form.data_type,
      });
      toast.success(`Added custom ${form.kind} “${form.name}”.`);
      setDialogOpen(false);
      setForm({ kind: "dimension", name: "", data_type: "string" });
      await load();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not add field.");
    }
  }

  async function remove(id: string) {
    try {
      await api.deleteSchemaExtension(id);
      await load();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not delete field.");
    }
  }

  if (error) return <ErrorBanner message={error} />;
  if (exts === null || resolved === null) return <Loading label="Loading schema…" />;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <p className="max-w-2xl text-sm text-muted-foreground">
          Extend the canonical schema with your own dimensions, measures, and factors — no code, no
          migration. Custom fields appear everywhere (mapping, stacks, export). An optional
          expression (e.g. <span className="mono">clicks &lt;= impressions</span>) runs as a
          sandboxed validation check.
        </p>
        <Button onClick={() => setDialogOpen(true)}>
          <Plus className="h-4 w-4" /> Add field
        </Button>
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold">Custom fields ({exts.length})</h3>
        {exts.length === 0 ? (
          <EmptyState
            icon={<Boxes className="h-6 w-6" />}
            title="No custom fields"
            description="Add a dimension, measure, or factor to tailor the schema for this customer."
          />
        ) : (
          <Table>
            <THead>
              <TR>
                <TH>Name</TH>
                <TH>Kind</TH>
                <TH>Type</TH>
                <TH>Check</TH>
                <TH className="text-right">Actions</TH>
              </TR>
            </THead>
            <tbody>
              {exts.map((e) => (
                <TR key={e.id} className="hover:bg-muted/40">
                  <TD className="font-medium">{e.name}</TD>
                  <TD>
                    <Badge variant="secondary">{e.kind}</Badge>
                  </TD>
                  <TD className="text-muted-foreground">{e.data_type}</TD>
                  <TD className="mono text-xs text-muted-foreground">{e.validation ?? "—"}</TD>
                  <TD className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => remove(e.id)}
                      aria-label="Delete"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TD>
                </TR>
              ))}
            </tbody>
          </Table>
        )}
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold">Resolved schema (core + extensions)</h3>
        <div className="flex flex-wrap gap-1.5">
          {resolved.map((f) => (
            <span
              key={`${f.kind}-${f.name}`}
              className={cn(
                "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs",
                f.source === "extension"
                  ? "border-primary/40 text-primary"
                  : "border-border text-muted-foreground"
              )}
              title={`${f.kind} · ${f.type} · ${f.source}`}
            >
              {f.name}
              {f.source === "extension" ? <Badge variant="default">custom</Badge> : null}
            </span>
          ))}
        </div>
      </div>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} title="Add a custom field">
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Kind</label>
              <select
                className={inputCls}
                value={form.kind}
                onChange={(e) => setForm({ ...form, kind: e.target.value })}
              >
                <option value="dimension">dimension</option>
                <option value="measure">measure</option>
                <option value="factor">factor</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Data type</label>
              <select
                className={inputCls}
                value={form.data_type}
                onChange={(e) => setForm({ ...form, data_type: e.target.value })}
              >
                <option value="string">string</option>
                <option value="number">number</option>
                <option value="date">date</option>
                <option value="boolean">boolean</option>
              </select>
            </div>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Field name</label>
            <input
              className={inputCls}
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="brand"
            />
          </div>
          <p className="text-xs text-muted-foreground">
            Need a business-rule check (e.g. clicks ≤ impressions)? Add it under the{" "}
            <span className="font-medium">Validation rules</span> tab — rules run across all data,
            not just this field.
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="outline" size="sm" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={create} disabled={!form.name.trim()}>
              Add field
            </Button>
          </div>
        </div>
      </Dialog>
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

/** Custom validation rules (Part 3): tenant-authored semantic checks. */
function ValidationRulesTab() {
  const toast = useToast();
  const [rules, setRules] = useState<ValidationRule[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState({ name: "", expression: "", severity: "blocking" });

  const load = useCallback(async () => {
    try {
      setRules(await api.listValidationRules());
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load rules.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function create() {
    try {
      await api.createValidationRule({
        name: form.name.trim(),
        expression: form.expression.trim(),
        severity: form.severity,
      });
      toast.success(`Added rule “${form.name}”.`);
      setDialogOpen(false);
      setForm({ name: "", expression: "", severity: "blocking" });
      await load();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not add rule.");
    }
  }

  async function toggle(rule: ValidationRule) {
    try {
      await api.updateValidationRule(rule.id, { enabled: !rule.enabled });
      await load();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not update rule.");
    }
  }

  async function remove(id: string) {
    try {
      await api.deleteValidationRule(id);
      await load();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not delete rule.");
    }
  }

  if (error) return <ErrorBanner message={error} />;
  if (rules === null) return <Loading label="Loading validation rules…" />;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <p className="max-w-2xl text-sm text-muted-foreground">
          Meaningful, business-rule validation authored as a safe expression (e.g.{" "}
          <span className="mono">clicks &lt;= impressions</span>). Rules run automatically across
          every pipeline run, sheet validation, and Stack publish. Blocking rules stop output until
          resolved or overridden.
        </p>
        <Button onClick={() => setDialogOpen(true)}>
          <Plus className="h-4 w-4" /> Add rule
        </Button>
      </div>

      {rules.length === 0 ? (
        <EmptyState
          icon={<ListChecks className="h-6 w-6" />}
          title="No custom rules"
          description="Add a business-rule check to catch data errors the built-in checks don't."
        />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Name</TH>
              <TH>Expression</TH>
              <TH>Severity</TH>
              <TH>Enabled</TH>
              <TH className="text-right">Actions</TH>
            </TR>
          </THead>
          <tbody>
            {rules.map((r) => (
              <TR key={r.id} className="hover:bg-muted/40">
                <TD className="font-medium">{r.name}</TD>
                <TD className="mono text-xs text-muted-foreground">{r.expression}</TD>
                <TD>
                  <Badge variant={statusVariant(r.severity)}>{r.severity}</Badge>
                </TD>
                <TD>
                  <button
                    type="button"
                    onClick={() => toggle(r)}
                    className={cn(
                      "rounded-full px-2 py-0.5 text-xs font-medium",
                      r.enabled ? "bg-success/12 text-success" : "bg-muted text-muted-foreground"
                    )}
                  >
                    {r.enabled ? "enabled" : "disabled"}
                  </button>
                </TD>
                <TD className="text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => remove(r.id)}
                    aria-label="Delete"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </TD>
              </TR>
            ))}
          </tbody>
        </Table>
      )}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} title="Add a validation rule">
        <div className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Rule name</label>
            <input
              className={inputCls}
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="clicks under impressions"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">
              Expression (must be true to pass)
            </label>
            <input
              className={inputCls}
              value={form.expression}
              onChange={(e) => setForm({ ...form, expression: e.target.value })}
              placeholder="clicks <= impressions"
            />
            <span className="block text-xs text-muted-foreground">
              Sandboxed — fields, comparisons, and a small function allowlist only.
            </span>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Severity</label>
            <select
              className={inputCls}
              value={form.severity}
              onChange={(e) => setForm({ ...form, severity: e.target.value })}
            >
              <option value="blocking">blocking (stops output)</option>
              <option value="warning">warning</option>
              <option value="info">info</option>
            </select>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" size="sm" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={create}
              disabled={!form.name.trim() || !form.expression.trim()}
            >
              Add rule
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
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

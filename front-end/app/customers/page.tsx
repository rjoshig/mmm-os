"use client";

import { Building2, Copy, DatabaseZap, Plus } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataTable, type DataColumn } from "@/components/ui/data-table";
import { Dialog } from "@/components/ui/dialog";
import { SearchableSelect } from "@/components/ui/searchable-select";
import { EmptyState, ErrorBanner } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
import { TableSkeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { CustomerOnboardingWizard } from "@/components/onboarding/customer-onboarding-wizard";
import { api, ApiError } from "@/lib/api/client";
import type { Customer } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { setSelectedWorkspaceId } from "@/lib/tenant";

const inputCls =
  "h-9 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

export default function CustomersPage() {
  const toast = useToast();
  const [customers, setCustomers] = useState<Customer[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [isolationFor, setIsolationFor] = useState<Customer | null>(null);
  const [copyOpen, setCopyOpen] = useState(false);
  const [copyTarget, setCopyTarget] = useState("");
  const [copying, setCopying] = useState(false);

  async function copyConfigs() {
    if (!copyTarget) return;
    setCopying(true);
    try {
      const res = await api.cloneCustomerConfigs(copyTarget);
      const total = Object.values(res.counts).reduce((a, b) => a + b, 0);
      toast.success(`Copied ${total} config item(s) to the target customer.`);
      setCopyOpen(false);
      setCopyTarget("");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not copy configs.");
    } finally {
      setCopying(false);
    }
  }

  const load = useCallback(async () => {
    try {
      setCustomers(await api.listCustomers());
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load customers.");
      setCustomers([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function openWorkspace(id: string) {
    setSelectedWorkspaceId(id);
    window.location.assign("/");
  }

  const columns: DataColumn<Customer>[] = [
    {
      key: "name",
      header: "Customer",
      cell: (c) => <span className="font-medium">{c.name}</span>,
      sortKey: (c) => c.name,
    },
    { key: "slug", header: "Slug", cell: (c) => <span className="mono text-xs">{c.slug}</span> },
    {
      key: "tier",
      header: "Tier",
      cell: (c) => (
        <Badge variant={c.tier === "enterprise" ? "default" : "secondary"}>{c.tier}</Badge>
      ),
      sortKey: (c) => c.tier,
    },
    {
      key: "region",
      header: "Region",
      cell: (c) => c.region.toUpperCase(),
      sortKey: (c) => c.region,
    },
    {
      key: "status",
      header: "Status",
      cell: (c) => (
        <Badge variant={c.status === "active" ? "success" : "warning"}>{c.status}</Badge>
      ),
      sortKey: (c) => c.status,
    },
    {
      key: "isolation",
      header: "Isolation",
      cell: (c) => (
        <Badge variant={c.isolation_mode === "silo" ? "default" : "secondary"}>
          {c.isolation_mode === "silo" ? "Dedicated DB" : "Shared pool"}
        </Badge>
      ),
      sortKey: (c) => c.isolation_mode,
    },
    {
      key: "created",
      header: "Created",
      cell: (c) => <span className="text-muted-foreground">{formatDateTime(c.created_at)}</span>,
      sortKey: (c) => c.created_at,
    },
    {
      key: "actions",
      header: "",
      align: "right",
      cell: (c) => (
        <div className="flex justify-end gap-2">
          {c.tier === "enterprise" ? (
            <Button variant="ghost" size="sm" onClick={() => setIsolationFor(c)}>
              <DatabaseZap className="h-4 w-4" /> Isolation
            </Button>
          ) : null}
          <Button variant="outline" size="sm" onClick={() => openWorkspace(c.id)}>
            Open workspace
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <CustomerOnboardingWizard
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onDone={() => {
          setDialogOpen(false);
          void load();
        }}
      />
      <IsolationDialog
        customer={isolationFor}
        onClose={() => setIsolationFor(null)}
        onSaved={(c) => {
          setIsolationFor(null);
          toast.success(
            c.isolation_mode === "silo"
              ? `"${c.name}" moved to a dedicated database.`
              : `"${c.name}" moved to the shared pool.`
          );
          void load();
        }}
      />
      <PageHeader
        eyebrow="Platform"
        title="Customers"
        description="Each customer is an isolated workspace (all data tenant-scoped, CC-1). Onboard a customer, then switch into their workspace to connect partners and map files."
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => setCopyOpen(true)}>
              <Copy className="h-4 w-4" /> Copy configs to…
            </Button>
            <Button onClick={() => setDialogOpen(true)}>
              <Plus className="h-4 w-4" /> New customer
            </Button>
          </div>
        }
      />

      <Dialog
        open={copyOpen}
        onClose={() => setCopyOpen(false)}
        title="Copy this workspace's configs"
        description="Clone the active workspace's mappings, rule sets, feed templates, and connector configs (never credentials) into another customer."
      >
        <div className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Target customer</label>
            <SearchableSelect
              value={copyTarget}
              onChange={setCopyTarget}
              placeholder="Choose a customer"
              options={(customers ?? []).map((c) => ({ value: c.id, label: c.name, hint: c.slug }))}
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" size="sm" onClick={() => setCopyOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={copyConfigs} disabled={copying || !copyTarget}>
              {copying ? "Copying…" : "Copy configs"}
            </Button>
          </div>
        </div>
      </Dialog>

      {error ? <ErrorBanner message={error} /> : null}

      {customers === null ? (
        <TableSkeleton rows={4} cols={6} />
      ) : customers.length === 0 ? (
        <EmptyState
          icon={<Building2 className="h-6 w-6" />}
          title="No customers yet"
          description="Onboard your first customer workspace to begin."
          action={
            <Button onClick={() => setDialogOpen(true)}>
              <Plus className="h-4 w-4" /> New customer
            </Button>
          }
        />
      ) : (
        <DataTable
          rows={customers}
          columns={columns}
          rowKey={(c) => c.id}
          search={(c) => `${c.name} ${c.slug} ${c.tier} ${c.region}`}
          searchPlaceholder="Search customers…"
          initialSort={{ key: "created", dir: "desc" }}
        />
      )}
    </div>
  );
}

function IsolationDialog({
  customer,
  onClose,
  onSaved,
}: {
  customer: Customer | null;
  onClose: () => void;
  onSaved: (c: Customer) => void;
}) {
  const [dbUrl, setDbUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const isSilo = customer?.isolation_mode === "silo";

  async function apply(mode: "pool" | "silo") {
    if (!customer) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await api.setCustomerIsolation(customer.id, {
        mode,
        database_url: mode === "silo" ? dbUrl.trim() : undefined,
      });
      setDbUrl("");
      onSaved(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update isolation.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog
      open={customer !== null}
      onClose={onClose}
      title={`Isolation — ${customer?.name ?? ""}`}
      description="Standard customers share the pool database (row-level tenant scoping). Enterprise customers can run on a dedicated database; its URL is stored encrypted (never in plaintext)."
    >
      <div className="space-y-4">
        <div className="rounded-md border border-border bg-muted/40 px-3 py-2 text-sm">
          Current:{" "}
          <span className="font-medium">{isSilo ? "Dedicated DB (silo)" : "Shared pool"}</span>
        </div>
        {!isSilo ? (
          <label className="block space-y-1.5">
            <span className="text-sm font-medium">Dedicated database URL</span>
            <input
              className={inputCls}
              placeholder="postgresql+psycopg://…  or  sqlite:///walmart.db"
              value={dbUrl}
              onChange={(e) => setDbUrl(e.target.value)}
            />
            <span className="text-xs text-muted-foreground">
              Schema is provisioned automatically. Routing activates when MULTI_DB_ROUTING_ENABLED
              is on.
            </span>
          </label>
        ) : (
          <p className="text-sm text-muted-foreground">
            This customer runs on a dedicated database. You can return it to the shared pool below.
          </p>
        )}
        {error ? <ErrorBanner message={error} /> : null}
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          {isSilo ? (
            <Button variant="outline" onClick={() => apply("pool")} disabled={saving}>
              {saving ? "Moving…" : "Move to shared pool"}
            </Button>
          ) : (
            <Button onClick={() => apply("silo")} disabled={saving || !dbUrl.trim()}>
              {saving ? "Provisioning…" : "Move to dedicated DB"}
            </Button>
          )}
        </div>
      </div>
    </Dialog>
  );
}

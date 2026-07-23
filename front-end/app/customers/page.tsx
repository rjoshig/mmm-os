"use client";

import { Building2, Plus } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataTable, type DataColumn } from "@/components/ui/data-table";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState, ErrorBanner } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
import { TableSkeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
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
    { key: "region", header: "Region", cell: (c) => c.region.toUpperCase(), sortKey: (c) => c.region },
    {
      key: "status",
      header: "Status",
      cell: (c) => <Badge variant={c.status === "active" ? "success" : "warning"}>{c.status}</Badge>,
      sortKey: (c) => c.status,
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
        <Button variant="outline" size="sm" onClick={() => openWorkspace(c.id)}>
          Open workspace
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <NewCustomerDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onCreated={(c) => {
          setDialogOpen(false);
          toast.success(`Customer "${c.name}" onboarded.`);
          void load();
        }}
      />
      <PageHeader
        eyebrow="Platform"
        title="Customers"
        description="Each customer is an isolated workspace (all data tenant-scoped, CC-1). Onboard a customer, then switch into their workspace to connect partners and map files."
        actions={
          <Button onClick={() => setDialogOpen(true)}>
            <Plus className="h-4 w-4" /> New customer
          </Button>
        }
      />

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

function NewCustomerDialog({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (c: Customer) => void;
}) {
  const [name, setName] = useState("");
  const [tier, setTier] = useState("standard");
  const [region, setRegion] = useState("us");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function create() {
    setSaving(true);
    setError(null);
    try {
      const c = await api.createCustomer({ name: name.trim(), tier, region });
      setName("");
      onCreated(c);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create the customer.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Onboard a customer"
      description="Creates an isolated workspace. Enterprise tier can later be routed to a dedicated database."
    >
      <div className="space-y-4">
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">Customer name</span>
          <input
            className={inputCls}
            placeholder="Walmart"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </label>
        <div className="grid grid-cols-2 gap-3">
          <label className="block space-y-1.5">
            <span className="text-sm font-medium">Tier</span>
            <select className={inputCls} value={tier} onChange={(e) => setTier(e.target.value)}>
              <option value="standard">Standard (shared pool)</option>
              <option value="enterprise">Enterprise (dedicated DB option)</option>
            </select>
          </label>
          <label className="block space-y-1.5">
            <span className="text-sm font-medium">Region</span>
            <select className={inputCls} value={region} onChange={(e) => setRegion(e.target.value)}>
              <option value="us">US</option>
              <option value="eu">EU</option>
              <option value="apac">APAC</option>
            </select>
          </label>
        </div>
        {error ? <ErrorBanner message={error} /> : null}
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={create} disabled={saving || !name.trim()}>
            {saving ? "Onboarding…" : "Onboard customer"}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}

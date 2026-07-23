"use client";

import { Building2, CheckCircle2, KeyRound, Plug, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { ErrorBanner } from "@/components/ui/feedback";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api/client";
import type { AvailableConnector, Customer } from "@/lib/api/types";
import { setSelectedWorkspaceId } from "@/lib/tenant";

type Step = "create" | "partners" | "feeds" | "ready";

const inputCls =
  "h-9 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

const STEPS: { key: Step; label: string }[] = [
  { key: "create", label: "Workspace" },
  { key: "partners", label: "Partners" },
  { key: "feeds", label: "File feeds" },
  { key: "ready", label: "Ready" },
];

/**
 * Guided customer onboarding: create the workspace, connect partner APIs, register
 * recurring file feeds, and hand off a ready workspace. Sequences the platform +
 * tenant-scoped endpoints (Slices 7.1/7.3/7.4). After the workspace is created it is
 * set active, so the subsequent tenant-scoped calls target the new customer.
 */
export function CustomerOnboardingWizard({
  open,
  onClose,
  onDone,
}: {
  open: boolean;
  onClose: () => void;
  onDone: () => void;
}) {
  const toast = useToast();
  const [step, setStep] = useState<Step>("create");
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [partnerCount, setPartnerCount] = useState(0);
  const [feedCount, setFeedCount] = useState(0);

  useEffect(() => {
    if (open) {
      setStep("create");
      setCustomer(null);
      setPartnerCount(0);
      setFeedCount(0);
    }
  }, [open]);

  function finish() {
    if (customer) setSelectedWorkspaceId(customer.id);
    onDone();
    // Hard reload into the new workspace so every screen scopes to it.
    window.location.assign("/");
  }

  const activeIdx = STEPS.findIndex((s) => s.key === step);

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Onboard a customer"
      description="Create an isolated workspace, connect their partners and file feeds, and hand off model-ready data."
    >
      <div className="space-y-5">
        <ol className="flex items-center gap-2 text-xs">
          {STEPS.map((s, i) => (
            <li key={s.key} className="flex items-center gap-2">
              <span
                className={
                  i <= activeIdx
                    ? "flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground"
                    : "flex h-6 w-6 items-center justify-center rounded-full bg-muted text-muted-foreground"
                }
              >
                {i < activeIdx ? <CheckCircle2 className="h-4 w-4" /> : i + 1}
              </span>
              <span className={i === activeIdx ? "font-medium" : "text-muted-foreground"}>
                {s.label}
              </span>
              {i < STEPS.length - 1 ? <span className="text-muted-foreground">→</span> : null}
            </li>
          ))}
        </ol>

        {step === "create" ? (
          <CreateStep
            onCreated={(c) => {
              setCustomer(c);
              setSelectedWorkspaceId(c.id); // subsequent tenant-scoped calls target it
              setStep("partners");
            }}
          />
        ) : null}

        {step === "partners" && customer ? (
          <PartnersStep
            onCount={setPartnerCount}
            onNext={() => setStep("feeds")}
            onBack={() => setStep("create")}
          />
        ) : null}

        {step === "feeds" && customer ? (
          <FeedsStep
            onCount={setFeedCount}
            onNext={() => setStep("ready")}
            onBack={() => setStep("partners")}
          />
        ) : null}

        {step === "ready" && customer ? (
          <div className="space-y-4">
            <div className="rounded-md border border-border bg-muted/40 p-4 text-sm">
              <div className="mb-1 font-medium">{customer.name} is ready.</div>
              <ul className="list-disc space-y-0.5 pl-5 text-muted-foreground">
                <li>Isolated workspace created ({customer.tier} tier, {customer.region.toUpperCase()}).</li>
                <li>{partnerCount} partner connector{partnerCount === 1 ? "" : "s"} connected.</li>
                <li>{feedCount} file feed template{feedCount === 1 ? "" : "s"} registered.</li>
              </ul>
            </div>
            <p className="text-xs text-muted-foreground">
              Next in the workspace: trigger a sync or upload a feed, then map → validate → export.
            </p>
            <div className="flex justify-end gap-2">
              <Button
                onClick={() => {
                  toast.success(`${customer.name} onboarded.`);
                  finish();
                }}
              >
                Open workspace
              </Button>
            </div>
          </div>
        ) : null}
      </div>
    </Dialog>
  );
}

function CreateStep({ onCreated }: { onCreated: (c: Customer) => void }) {
  const [name, setName] = useState("");
  const [tier, setTier] = useState("standard");
  const [region, setRegion] = useState("us");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function create() {
    setSaving(true);
    setError(null);
    try {
      onCreated(await api.createCustomer({ name: name.trim(), tier, region }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create the workspace.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      <label className="block space-y-1.5">
        <span className="text-sm font-medium">Customer name</span>
        <input className={inputCls} placeholder="Walmart" value={name} onChange={(e) => setName(e.target.value)} />
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
      <div className="flex justify-end">
        <Button onClick={create} disabled={saving || !name.trim()}>
          {saving ? "Creating…" : "Create & continue"}
        </Button>
      </div>
    </div>
  );
}

function PartnersStep({
  onCount,
  onNext,
  onBack,
}: {
  onCount: (n: number) => void;
  onNext: () => void;
  onBack: () => void;
}) {
  const toast = useToast();
  const [available, setAvailable] = useState<AvailableConnector[]>([]);
  const [added, setAdded] = useState<string[]>([]);
  const [key, setKey] = useState("");
  const [name, setName] = useState("");
  const [accounts, setAccounts] = useState("");
  const [token, setToken] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .availableConnectors()
      .then((r) => {
        const partners = r.connectors.filter((c) => c.is_partner);
        setAvailable(partners);
        if (partners[0]) setKey(partners[0].key);
      })
      .catch(() => setAvailable([]));
  }, []);

  async function addPartner() {
    setSaving(true);
    setError(null);
    try {
      const config = await api.createConnectorConfig({
        connector_key: key,
        name: name.trim() || key,
        account_ids: accounts.split(",").map((a) => a.trim()).filter(Boolean),
      });
      if (token.trim()) {
        await api.setConnectorCredential(config.id, { token: token.trim() });
      }
      const next = [...added, `${config.name} (${key})`];
      setAdded(next);
      onCount(next.length);
      setName("");
      setAccounts("");
      setToken("");
      toast.success(`${key} connected.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not add the partner.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Connect the partner APIs this customer pulls from (optional — add any you have credentials for).
      </p>
      {added.length ? (
        <div className="flex flex-wrap gap-2">
          {added.map((a, i) => (
            <Badge key={i} variant="success">
              <Plug className="h-3 w-3" /> {a}
            </Badge>
          ))}
        </div>
      ) : null}
      <div className="space-y-3 rounded-md border border-border p-3">
        <div className="grid grid-cols-2 gap-3">
          <label className="block space-y-1.5">
            <span className="text-sm font-medium">Partner</span>
            <select className={inputCls} value={key} onChange={(e) => setKey(e.target.value)}>
              {available.map((c) => (
                <option key={c.key} value={c.key}>{c.key}</option>
              ))}
            </select>
          </label>
          <label className="block space-y-1.5">
            <span className="text-sm font-medium">Label</span>
            <input className={inputCls} placeholder="Meta – US" value={name} onChange={(e) => setName(e.target.value)} />
          </label>
        </div>
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">Account ids (comma-separated)</span>
          <input className={inputCls} placeholder="act_123, act_456" value={accounts} onChange={(e) => setAccounts(e.target.value)} />
        </label>
        <label className="block space-y-1.5">
          <span className="flex items-center gap-1 text-sm font-medium">
            <KeyRound className="h-3.5 w-3.5" /> API token (encrypted; optional now)
          </span>
          <input className={inputCls} type="password" autoComplete="off" placeholder="paste token" value={token} onChange={(e) => setToken(e.target.value)} />
        </label>
        {error ? <ErrorBanner message={error} /> : null}
        <Button variant="outline" size="sm" onClick={addPartner} disabled={saving || !key}>
          <Plus className="h-4 w-4" /> {saving ? "Adding…" : "Add partner"}
        </Button>
      </div>
      <div className="flex justify-between">
        <Button variant="ghost" onClick={onBack}>Back</Button>
        <Button onClick={onNext}>{added.length ? "Continue" : "Skip"}</Button>
      </div>
    </div>
  );
}

function FeedsStep({
  onCount,
  onNext,
  onBack,
}: {
  onCount: (n: number) => void;
  onNext: () => void;
  onBack: () => void;
}) {
  const toast = useToast();
  const [added, setAdded] = useState<string[]>([]);
  const [name, setName] = useState("");
  const [fmt, setFmt] = useState("delimited");
  const [columns, setColumns] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function addFeed() {
    setSaving(true);
    setError(null);
    try {
      const cols = columns.split(",").map((c) => c.trim()).filter(Boolean);
      await api.createFeedTemplate({
        name: name.trim(),
        fmt,
        expected_columns: fmt === "delimited" ? cols : [],
        // Fixed-width layouts are refined later on the File feeds screen.
        fixed_fields: fmt === "fixed_width" ? cols.map((c, i) => ({ name: c, start: i, width: 1 })) : [],
        has_header: fmt !== "fixed_width",
      });
      const next = [...added, `${name.trim()} (${fmt})`];
      setAdded(next);
      onCount(next.length);
      setName("");
      setColumns("");
      toast.success(`Feed "${name.trim()}" registered.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not register the feed.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Register the recurring files this customer sends (optional). Refine fixed-width layouts later on File feeds.
      </p>
      {added.length ? (
        <div className="flex flex-wrap gap-2">
          {added.map((a, i) => (
            <Badge key={i} variant="secondary">{a}</Badge>
          ))}
        </div>
      ) : null}
      <div className="space-y-3 rounded-md border border-border p-3">
        <div className="grid grid-cols-2 gap-3">
          <label className="block space-y-1.5">
            <span className="text-sm font-medium">Feed name</span>
            <input className={inputCls} placeholder="Daily store sales" value={name} onChange={(e) => setName(e.target.value)} />
          </label>
          <label className="block space-y-1.5">
            <span className="text-sm font-medium">Format</span>
            <select className={inputCls} value={fmt} onChange={(e) => setFmt(e.target.value)}>
              <option value="delimited">Delimited</option>
              <option value="fixed_width">Fixed-width</option>
              <option value="xlsx">Excel (.xlsx)</option>
            </select>
          </label>
        </div>
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">
            {fmt === "fixed_width" ? "Column names (comma-separated)" : "Expected columns (comma-separated)"}
          </span>
          <input className={inputCls} placeholder="date, store, spend" value={columns} onChange={(e) => setColumns(e.target.value)} />
        </label>
        {error ? <ErrorBanner message={error} /> : null}
        <Button variant="outline" size="sm" onClick={addFeed} disabled={saving || !name.trim()}>
          <Plus className="h-4 w-4" /> {saving ? "Adding…" : "Add feed"}
        </Button>
      </div>
      <div className="flex justify-between">
        <Button variant="ghost" onClick={onBack}>Back</Button>
        <Button onClick={onNext}>
          <Building2 className="h-4 w-4" /> {added.length ? "Continue" : "Skip"}
        </Button>
      </div>
    </div>
  );
}

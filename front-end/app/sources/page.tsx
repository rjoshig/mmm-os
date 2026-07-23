"use client";

import { ChevronDown, ChevronRight, Clock, Play, Plug, Plus, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Badge, statusVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState, ErrorBanner } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
import { TableSkeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api/client";
import type { AvailableConnector, ConnectorConfig, SyncRun } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";

const inputCls =
  "h-9 rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

// Schedule interval options (minutes). 0 = off.
const SCHEDULE_OPTIONS: { label: string; minutes: number }[] = [
  { label: "Off", minutes: 0 },
  { label: "Hourly", minutes: 60 },
  { label: "Every 6h", minutes: 360 },
  { label: "Daily", minutes: 1440 },
  { label: "Weekly", minutes: 10080 },
];

function scheduleMinutes(config: ConnectorConfig): number {
  const s = config.settings?.schedule as { interval_minutes?: number } | undefined;
  return typeof s?.interval_minutes === "number" ? s.interval_minutes : 0;
}

function RunDueButton({ onDone }: { onDone: () => void }) {
  const toast = useToast();
  const [running, setRunning] = useState(false);
  async function run() {
    setRunning(true);
    try {
      const { ran } = await api.runDueSyncs();
      toast.success(ran.length ? `Ran ${ran.length} due sync(s).` : "No syncs are due.");
      onDone();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Run-due failed.");
    } finally {
      setRunning(false);
    }
  }
  return (
    <Button variant="outline" onClick={run} disabled={running}>
      <Play className="h-4 w-4" />
      {running ? "Running…" : "Run due now"}
    </Button>
  );
}

export default function SourcesPage() {
  const toast = useToast();
  const [configs, setConfigs] = useState<ConnectorConfig[] | null>(null);
  const [available, setAvailable] = useState<AvailableConnector[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  const load = useCallback(async () => {
    try {
      const [cfgs, avail] = await Promise.all([
        api.listConnectorConfigs(),
        api.availableConnectors(),
      ]);
      setConfigs(cfgs);
      setAvailable(avail.connectors);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load sources.");
      setConfigs([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const partnerKeys = useMemo(
    () => new Set(available.filter((c) => c.is_partner).map((c) => c.key)),
    [available]
  );

  return (
    <div className="space-y-6">
      <NewSourceDialog
        open={dialogOpen}
        available={available}
        onClose={() => setDialogOpen(false)}
        onCreated={() => {
          setDialogOpen(false);
          void load();
        }}
      />
      <PageHeader
        eyebrow="Automation"
        title="Sources"
        description="Partner connectors and file sources that feed the pipeline. Configure a source, trigger a sync, and watch its run history."
        actions={
          <div className="flex items-center gap-2">
            <RunDueButton onDone={load} />
            <Button onClick={() => setDialogOpen(true)} disabled={available.length === 0}>
              <Plus className="h-4 w-4" /> New source
            </Button>
          </div>
        }
      />

      {error ? <ErrorBanner message={error} /> : null}

      {configs === null ? (
        <TableSkeleton rows={4} cols={4} />
      ) : configs.length === 0 ? (
        <EmptyState
          icon={<Plug className="h-6 w-6" />}
          title="No sources yet"
          description="Add a partner connector (Meta, Google Ads, DV360, TikTok) or an SFTP file source to automate ingestion."
          action={
            <Button onClick={() => setDialogOpen(true)} disabled={available.length === 0}>
              <Plus className="h-4 w-4" /> New source
            </Button>
          }
        />
      ) : (
        <div className="space-y-3">
          {configs.map((config) => (
            <SourceCard
              key={config.id}
              config={config}
              isPartner={partnerKeys.has(config.connector_key)}
              onSynced={load}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function SourceCard({
  config,
  isPartner,
  onSynced,
}: {
  config: ConnectorConfig;
  isPartner: boolean;
  onSynced: () => void;
}) {
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [runs, setRuns] = useState<SyncRun[] | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [interval, setIntervalMin] = useState(scheduleMinutes(config));

  async function onSchedule(minutes: number) {
    setIntervalMin(minutes);
    try {
      await api.setConnectorSchedule(config.id, minutes || null);
      toast.success(minutes ? "Schedule updated." : "Schedule turned off.");
      onSynced();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not update schedule.");
    }
  }

  const loadRuns = useCallback(async () => {
    try {
      setRuns(await api.listSyncRuns(config.id));
    } catch {
      setRuns([]);
    }
  }, [config.id]);

  useEffect(() => {
    if (open && runs === null) void loadRuns();
  }, [open, runs, loadRuns]);

  async function onSync() {
    setSyncing(true);
    try {
      const run = await api.triggerSync(config.id);
      toast.success(`Sync ${run.status} — ${run.row_count ?? 0} row(s).`);
      setOpen(true);
      await loadRuns();
      onSynced();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Sync failed.");
    } finally {
      setSyncing(false);
    }
  }

  const lastRun = runs?.[0] ?? null;

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
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="truncate text-sm font-medium">{config.name}</span>
            <Badge variant="secondary">{config.connector_key}</Badge>
            {config.enabled ? null : <Badge variant="warning">disabled</Badge>}
          </div>
          <div className="text-xs text-muted-foreground">
            {config.account_ids.length} account{config.account_ids.length === 1 ? "" : "s"}
            {lastRun ? ` · last run ${formatDateTime(lastRun.finished_at ?? lastRun.started_at ?? "")}` : ""}
          </div>
        </div>
        <div className="ml-auto flex items-center gap-2">
          {lastRun ? <Badge variant={statusVariant(lastRun.status)}>{lastRun.status}</Badge> : null}
          {isPartner ? (
            <>
              <label className="flex items-center gap-1 text-xs text-muted-foreground">
                <Clock className="h-3.5 w-3.5" />
                <select
                  className="h-8 rounded-md border border-input bg-background px-2 text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  value={interval}
                  onChange={(e) => onSchedule(Number(e.target.value))}
                >
                  {SCHEDULE_OPTIONS.map((o) => (
                    <option key={o.minutes} value={o.minutes}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>
              <Button variant="outline" size="sm" onClick={onSync} disabled={syncing}>
                <RefreshCw className={`h-3.5 w-3.5 ${syncing ? "animate-spin" : ""}`} />
                {syncing ? "Syncing…" : "Sync now"}
              </Button>
            </>
          ) : (
            <span className="text-xs text-muted-foreground">file source</span>
          )}
        </div>
      </div>

      {open ? (
        <div className="border-t border-border p-4">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Sync runs
          </h3>
          {runs === null ? (
            <p className="text-xs text-muted-foreground">Loading…</p>
          ) : runs.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              No runs yet.{isPartner ? " Trigger a sync to backfill this source." : ""}
            </p>
          ) : (
            <div className="space-y-1.5">
              {runs.slice(0, 8).map((run) => (
                <div key={run.id} className="flex flex-wrap items-center gap-3 text-sm">
                  <Badge variant={statusVariant(run.status)}>{run.status}</Badge>
                  <span className="font-mono text-xs text-muted-foreground">
                    {run.window_start} → {run.window_end}
                  </span>
                  <span className="tabular-nums text-muted-foreground">
                    {run.row_count ?? 0} rows
                  </span>
                  {run.error ? <span className="text-xs text-destructive">{run.error}</span> : null}
                  <span className="ml-auto text-xs text-muted-foreground">
                    {formatDateTime(run.finished_at ?? run.started_at ?? "")}
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

function NewSourceDialog({
  open,
  available,
  onClose,
  onCreated,
}: {
  open: boolean;
  available: AvailableConnector[];
  onClose: () => void;
  onCreated: () => void;
}) {
  const toast = useToast();
  const [connectorKey, setConnectorKey] = useState("");
  const [name, setName] = useState("");
  const [accounts, setAccounts] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open && available.length && !connectorKey) setConnectorKey(available[0].key);
  }, [open, available, connectorKey]);

  async function onCreate() {
    setSaving(true);
    setError(null);
    try {
      await api.createConnectorConfig({
        connector_key: connectorKey,
        name: name.trim(),
        account_ids: accounts
          .split(",")
          .map((a) => a.trim())
          .filter(Boolean),
      });
      toast.success(`Source "${name.trim()}" created.`);
      setName("");
      setAccounts("");
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create the source.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="New source"
      description="Configure a partner connector or file source for this tenant."
    >
      <div className="space-y-4">
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">Connector</span>
          <select
            className={`${inputCls} w-full`}
            value={connectorKey}
            onChange={(e) => setConnectorKey(e.target.value)}
          >
            {available.map((c) => (
              <option key={c.key} value={c.key}>
                {c.key}
                {c.is_partner ? "" : " (file source)"}
              </option>
            ))}
          </select>
        </label>
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">Name</span>
          <input
            className={`${inputCls} w-full`}
            placeholder="Meta — US brand account"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </label>
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">Account IDs</span>
          <input
            className={`${inputCls} w-full`}
            placeholder="act_123, act_456"
            value={accounts}
            onChange={(e) => setAccounts(e.target.value)}
          />
          <span className="block text-xs text-muted-foreground">Comma-separated.</span>
        </label>
        {error ? <ErrorBanner message={error} /> : null}
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={onCreate} disabled={saving || !connectorKey || !name.trim()}>
            {saving ? "Creating…" : "Create source"}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}

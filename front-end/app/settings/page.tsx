"use client";

import { Plus, Save, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { ErrorBanner, Loading } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api/client";
import type { TenantSettings } from "@/lib/api/types";

const inputCls =
  "h-9 rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

type FxRow = { currency: string; rate: string };

export default function SettingsPage() {
  const toast = useToast();
  const [settings, setSettings] = useState<TenantSettings | null>(null);
  const [currency, setCurrency] = useState("USD");
  const [timezone, setTimezone] = useState("UTC");
  const [fx, setFx] = useState<FxRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const s = await api.getSettings();
        setSettings(s);
        setCurrency(s.reporting_currency);
        setTimezone(s.reporting_timezone);
        setFx(Object.entries(s.fx_rates).map(([c, r]) => ({ currency: c, rate: String(r) })));
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load settings.");
      }
    })();
  }, []);

  const fxRates = useMemo(() => {
    const out: Record<string, number> = {};
    for (const { currency: c, rate } of fx) {
      const code = c.trim().toUpperCase();
      const value = Number(rate);
      if (code && Number.isFinite(value) && value > 0) out[code] = value;
    }
    return out;
  }, [fx]);

  async function onSave() {
    setSaving(true);
    setError(null);
    try {
      const saved = await api.updateSettings({
        reporting_currency: currency.trim().toUpperCase(),
        reporting_timezone: timezone.trim(),
        fx_rates: fxRates,
      });
      setSettings(saved);
      setFx(Object.entries(saved.fx_rates).map(([c, r]) => ({ currency: c, rate: String(r) })));
      toast.success("Reporting settings saved.");
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Save failed.";
      setError(msg);
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Reporting"
        title="Settings"
        description="The reporting frame every output normalizes to — currency, timezone, and FX rates. Used by convert-currency (to reporting) and normalize-timezone transforms."
        actions={
          <Button onClick={onSave} disabled={saving || settings === null}>
            <Save className="h-4 w-4" />
            {saving ? "Saving…" : "Save settings"}
          </Button>
        }
      />

      {error ? <ErrorBanner message={error} /> : null}

      {settings === null ? (
        <Loading label="Loading settings…" />
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <label className="space-y-1.5">
              <span className="text-sm font-medium">Reporting currency</span>
              <input
                className={`${inputCls} w-full`}
                value={currency}
                maxLength={3}
                placeholder="USD"
                onChange={(e) => setCurrency(e.target.value)}
              />
              <span className="block text-xs text-muted-foreground">ISO 4217 code (e.g. USD, EUR).</span>
            </label>
            <label className="space-y-1.5">
              <span className="text-sm font-medium">Reporting timezone</span>
              <input
                className={`${inputCls} w-full`}
                value={timezone}
                placeholder="UTC"
                onChange={(e) => setTimezone(e.target.value)}
              />
              <span className="block text-xs text-muted-foreground">IANA name (e.g. UTC, America/New_York).</span>
            </label>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold">FX rates → {currency.toUpperCase() || "reporting"}</h2>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setFx((rows) => [...rows, { currency: "", rate: "" }])}
              >
                <Plus className="h-3.5 w-3.5" /> Add rate
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Multiplier from a source currency into the reporting currency. The reporting
              currency itself is always 1.0.
            </p>
            {fx.length === 0 ? (
              <p className="rounded-md border border-dashed border-border px-3 py-4 text-center text-xs text-muted-foreground">
                No FX rates yet. Add one per source currency you receive.
              </p>
            ) : (
              <div className="space-y-2">
                {fx.map((row, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <input
                      className={`${inputCls} w-32`}
                      placeholder="EUR"
                      maxLength={3}
                      value={row.currency}
                      onChange={(e) =>
                        setFx((rows) => rows.map((r, j) => (j === i ? { ...r, currency: e.target.value } : r)))
                      }
                    />
                    <span className="text-muted-foreground">×</span>
                    <input
                      className={`${inputCls} w-32 tabular-nums`}
                      type="number"
                      step="any"
                      placeholder="1.08"
                      value={row.rate}
                      onChange={(e) =>
                        setFx((rows) => rows.map((r, j) => (j === i ? { ...r, rate: e.target.value } : r)))
                      }
                    />
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setFx((rows) => rows.filter((_, j) => j !== i))}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

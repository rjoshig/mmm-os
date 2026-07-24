"use client";

import { AlertTriangle, ArrowLeft, Download, HardDriveUpload, Rocket } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Badge, statusVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SimpleBarChart, MiniBars, token, type BarDatum } from "@/components/ui/chart";
import { ErrorBanner, Loading } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api/client";
import type { PublishStackResponse, StackDetail } from "@/lib/api/types";

export default function StackDetailPage() {
  const { stackId } = useParams<{ stackId: string }>();
  const { success, error: toastError, info } = useToast();
  const [stack, setStack] = useState<StackDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [blocking, setBlocking] = useState<PublishStackResponse["blocking_flags"]>([]);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setStack(await api.getStack(stackId));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load the stack.");
    }
  }, [stackId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function publish(force: boolean) {
    setBusy(true);
    try {
      const res = await api.publishStack(stackId, force);
      if (res.published) {
        success("Stack published — ready for modelling.");
        setBlocking([]);
        await load();
      } else {
        setBlocking(res.blocking_flags);
        info("Publish blocked by panel validation — resolve or force.");
      }
    } catch (e) {
      toastError(e instanceof Error ? e.message : "Could not publish.");
    } finally {
      setBusy(false);
    }
  }

  async function exportCsv() {
    try {
      const blob = await api.fetchStackCsv(stackId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${stack?.name ?? "stack"}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      toastError(e instanceof Error ? e.message : "Could not export CSV.");
    }
  }

  if (error) return <ErrorBanner message={error} />;
  if (!stack) return <Loading label="Loading stack…" />;

  const meanData: BarDatum[] = stack.measures
    .filter((m) => m.mean != null)
    .map((m) => ({ label: m.measure, value: Number(m.mean) }));
  const nullData: BarDatum[] = stack.measures.map((m) => ({
    label: m.measure,
    value: Math.round(m.null_rate * 100),
    color: m.null_rate > 0.2 ? token("destructive") : token("primary"),
  }));
  const published = stack.lifecycle_status === "published";

  return (
    <div className="space-y-6">
      <Link href="/stacks" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" /> Stacks
      </Link>

      <PageHeader
        eyebrow="Model-ready panel (Gold)"
        title={stack.name}
        description={stack.description ?? "Assembled from cleaned per-source outputs and harmonized across sources."}
        actions={
          <div className="flex items-center gap-2">
            <Badge variant={statusVariant(stack.lifecycle_status)}>{stack.lifecycle_status}</Badge>
            <Button variant="outline" size="sm" onClick={exportCsv}>
              <Download className="h-4 w-4" /> Export CSV
            </Button>
            {!published && (
              <Button size="sm" onClick={() => publish(false)} disabled={busy}>
                <Rocket className="h-4 w-4" /> Publish
              </Button>
            )}
          </div>
        }
      />

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Stat label="Rows" value={stack.row_count.toLocaleString()} />
        <Stat label="Sources" value={String(stack.source_job_ids.length)} />
        <Stat label="Grain" value={stack.grain ?? "—"} />
        <Stat label="Currency" value={stack.reporting_currency ?? "—"} />
      </div>

      {blocking.length > 0 && (
        <Card className="border-destructive/40">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertTriangle className="h-4 w-4" /> Publish blocked — {blocking.length} panel issue(s)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {blocking.map((f, i) => (
              <div key={i} className="flex items-center gap-2 text-sm">
                <Badge variant="destructive">{f.check}</Badge>
                <span className="text-muted-foreground">{f.description}</span>
              </div>
            ))}
            <div className="pt-2">
              <Button variant="destructive" size="sm" onClick={() => publish(true)} disabled={busy}>
                Publish anyway (override)
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Measure averages</CardTitle>
          </CardHeader>
          <CardContent>
            {meanData.length ? (
              <SimpleBarChart data={meanData} valueLabel="mean" />
            ) : (
              <p className="text-sm text-muted-foreground">No numeric measures in this panel.</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Null rate by measure</CardTitle>
          </CardHeader>
          <CardContent>
            {nullData.length ? (
              <MiniBars data={nullData} />
            ) : (
              <p className="text-sm text-muted-foreground">No measures to profile.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Output statistics</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted-foreground">
                <th className="py-2 pr-4">Measure</th>
                <th className="py-2 pr-4 text-right">Min</th>
                <th className="py-2 pr-4 text-right">Max</th>
                <th className="py-2 pr-4 text-right">Mean</th>
                <th className="py-2 pr-4 text-right">Median</th>
                <th className="py-2 pr-4 text-right">Std dev</th>
                <th className="py-2 pr-4 text-right">Null %</th>
              </tr>
            </thead>
            <tbody className="tabular-nums">
              {stack.measures.map((m) => (
                <tr key={m.measure} className="border-b border-border/60">
                  <td className="py-2 pr-4 font-medium">{m.measure}</td>
                  <td className="py-2 pr-4 text-right">{fmt(m.min)}</td>
                  <td className="py-2 pr-4 text-right">{fmt(m.max)}</td>
                  <td className="py-2 pr-4 text-right">{fmt(m.mean)}</td>
                  <td className="py-2 pr-4 text-right">{fmt(m.median)}</td>
                  <td className="py-2 pr-4 text-right">{fmt(m.stddev)}</td>
                  <td className="py-2 pr-4 text-right">{Math.round(m.null_rate * 100)}%</td>
                </tr>
              ))}
              {stack.measures.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-3 text-muted-foreground">
                    No measures in this panel yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <HardDriveUpload className="h-3.5 w-3.5" />
        Lineage: every row traces back through its source output to the raw file (CC-3).
      </p>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="text-xs text-muted-foreground">{label}</div>
        <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
      </CardContent>
    </Card>
  );
}

function fmt(v: number | null): string {
  if (v == null) return "—";
  return Math.abs(v) >= 1000 ? v.toLocaleString(undefined, { maximumFractionDigits: 0 }) : String(v);
}

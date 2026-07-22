"use client";

import { ArrowLeft, Plus, Save } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { OPERATIONS, RuleConfig, type UiRule } from "@/components/transform/rule-config";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorBanner, Loading } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
import { Table, TD, TH, THead, TR } from "@/components/ui/table";
import { api, ApiError } from "@/lib/api/client";
import type { PreviewResponse, RuleSpecIn, SheetDetail } from "@/lib/api/types";
import { sampleRowsFromProfile } from "@/lib/sample";

let ruleSeq = 0;
function newRule(): UiRule {
  ruleSeq += 1;
  return { id: `r${ruleSeq}`, operation: "normalize_text", target_field: "", params: {} };
}

function toSpec(rule: UiRule, order: number): RuleSpecIn {
  return { operation: rule.operation, target_field: rule.target_field, params: rule.params, order };
}

export default function TransformBuilderPage() {
  const { sheetId } = useParams<{ sheetId: string }>();
  const [sheet, setSheet] = useState<SheetDetail | null>(null);
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [rules, setRules] = useState<UiRule[]>([]);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const columns = useMemo(() => (sheet?.sheet.columns ?? []).map((c) => c.name), [sheet]);

  useEffect(() => {
    (async () => {
      try {
        const detail = await api.getSheet(sheetId);
        setSheet(detail);
        setRows(sampleRowsFromProfile(detail));
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load sheet.");
      }
    })();
  }, [sheetId]);

  const runPreview = useCallback(async () => {
    if (rows.length === 0) return;
    const specs = rules.filter((r) => r.operation).map(toSpec);
    if (specs.length === 0) {
      setPreview(null);
      setPreviewError(null);
      return;
    }
    try {
      setPreview(await api.previewRules(rows, specs));
      setPreviewError(null);
    } catch (err) {
      setPreviewError(err instanceof ApiError ? err.message : "Preview failed.");
    }
  }, [rows, rules]);

  useEffect(() => {
    const t = setTimeout(runPreview, 300);
    return () => clearTimeout(t);
  }, [runPreview]);

  async function onSave() {
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const res = await api.saveRuleSet(`rules v${Date.now()}`, rules.map(toSpec));
      setNotice(`Saved rule set (v${res.version}, ${res.rules.length} rule(s)).`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Save failed.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      {sheet ? (
        <Link
          href={`/files/${sheet.sheet.file_id}`}
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back to file
        </Link>
      ) : null}

      <PageHeader
        eyebrow="Transformation builder"
        title={sheet?.sheet.sheet_name ?? "Transform"}
        description="Add rules by picking a column and an operation. Preview updates live; no JSON required."
        actions={
          <>
            <Button variant="outline" onClick={() => setRules((r) => [...r, newRule()])}>
              <Plus className="h-4 w-4" /> Add rule
            </Button>
            <Button onClick={onSave} disabled={saving || rules.length === 0}>
              <Save className="h-4 w-4" />
              {saving ? "Saving…" : "Save rule set"}
            </Button>
          </>
        }
      />

      {notice ? (
        <div className="rounded-md border border-success/30 bg-success/10 px-3 py-2 text-sm text-success">
          {notice}
        </div>
      ) : null}
      {error ? <ErrorBanner message={error} /> : null}

      {sheet === null ? (
        <Loading label="Loading sheet…" />
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="space-y-3">
            <h2 className="text-sm font-semibold">Rules</h2>
            {rules.length === 0 ? (
              <EmptyState
                title="No rules yet"
                description={`Add a rule to start. Available: ${OPERATIONS.map((o) => o.label).join(", ")}.`}
                action={
                  <Button variant="outline" onClick={() => setRules((r) => [...r, newRule()])}>
                    <Plus className="h-4 w-4" /> Add rule
                  </Button>
                }
              />
            ) : (
              rules.map((rule) => (
                <RuleConfig
                  key={rule.id}
                  rule={rule}
                  columns={columns}
                  onChange={(next) =>
                    setRules((rs) => rs.map((r) => (r.id === rule.id ? next : r)))
                  }
                  onRemove={() => setRules((rs) => rs.filter((r) => r.id !== rule.id))}
                />
              ))
            )}
          </div>

          <div className="space-y-3">
            <h2 className="text-sm font-semibold">Live preview (before → after)</h2>
            {rows.length === 0 ? (
              <EmptyState
                title="No sample data"
                description="This sheet has no profiled sample values to preview against."
              />
            ) : previewError ? (
              <ErrorBanner message={previewError} />
            ) : (
              <PreviewTables preview={preview} sampleRows={rows} />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function PreviewTables({
  preview,
  sampleRows,
}: {
  preview: PreviewResponse | null;
  sampleRows: Record<string, unknown>[];
}) {
  const before = preview?.before ?? sampleRows;
  const after = preview?.after ?? sampleRows;
  return (
    <div className="space-y-4">
      <PreviewGrid title="Before" rows={before} />
      <PreviewGrid title="After" rows={after} />
    </div>
  );
}

function PreviewGrid({ title, rows }: { title: string; rows: Record<string, unknown>[] }) {
  const cols = Array.from(new Set(rows.flatMap((r) => Object.keys(r))));
  return (
    <div>
      <div className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {title}
      </div>
      <Table>
        <THead>
          <TR>
            {cols.map((c) => (
              <TH key={c}>{c}</TH>
            ))}
          </TR>
        </THead>
        <tbody>
          {rows.slice(0, 6).map((row, i) => (
            <TR key={i}>
              {cols.map((c) => (
                <TD key={c} className="tabular-nums">
                  {row[c] == null ? (
                    <span className="text-muted-foreground">—</span>
                  ) : (
                    String(row[c])
                  )}
                </TD>
              ))}
            </TR>
          ))}
        </tbody>
      </Table>
    </div>
  );
}

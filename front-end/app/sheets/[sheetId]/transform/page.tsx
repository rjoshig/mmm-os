"use client";

import { ArrowLeft, Plus, Save, Sparkles } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { OPERATIONS, RuleConfig, type UiRule } from "@/components/transform/rule-config";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorBanner, Loading } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
import { useToast } from "@/components/ui/toast";
import { Tooltip } from "@/components/ui/tooltip";
import { api, ApiError } from "@/lib/api/client";
import type { PreviewResponse, RuleSpecIn, SheetDetail, SuggestionRead } from "@/lib/api/types";
import { cn } from "@/lib/utils";

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
  const toast = useToast();
  const [sheet, setSheet] = useState<SheetDetail | null>(null);
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [rules, setRules] = useState<UiRule[]>([]);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const columns = useMemo(() => (sheet?.sheet.columns ?? []).map((c) => c.name), [sheet]);
  const [ruleSetVersion, setRuleSetVersion] = useState<number | null>(null);
  const [aiSuggestions, setAiSuggestions] = useState<SuggestionRead[]>([]);
  const [aiLoading, setAiLoading] = useState(false);

  async function onSuggestAi() {
    setAiLoading(true);
    setError(null);
    try {
      const res = await api.suggestTransforms(sheetId);
      setAiSuggestions(res.suggestions);
      toast.success(
        res.suggestions.length
          ? `${res.suggestions.length} AI suggestion(s).`
          : "No transform suggestions — data looks clean."
      );
    } catch (err) {
      const msg =
        err instanceof ApiError && err.isLlmDisabled
          ? "AI is disabled — set LLM_ENABLED on the backend to use suggestions."
          : err instanceof ApiError
            ? err.message
            : "Could not get AI suggestions.";
      toast.error(msg);
    } finally {
      setAiLoading(false);
    }
  }

  function addSuggestion(s: SuggestionRead) {
    ruleSeq += 1;
    const p = s.payload as { operation?: string; target_field?: string; params?: Record<string, unknown> };
    setRules((rs) => [
      ...rs,
      {
        id: `r${ruleSeq}`,
        operation: String(p.operation ?? "normalize_text"),
        target_field: String(p.target_field ?? ""),
        params: p.params ?? {},
      },
    ]);
    setAiSuggestions((list) => list.filter((x) => x.id !== s.id));
    toast.success("Rule added to the builder — review and save.");
  }

  function dismissSuggestion(id: string) {
    setAiSuggestions((list) => list.filter((x) => x.id !== id));
  }

  useEffect(() => {
    (async () => {
      try {
        const [detail, sample] = await Promise.all([
          api.getSheet(sheetId),
          api.getSheetRows(sheetId, 20),
        ]);
        setSheet(detail);
        setRows(sample.rows);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load sheet.");
      }
      try {
        const existing = await api.getSheetRuleSet(sheetId);
        setRuleSetVersion(existing.version);
        setRules(
          existing.rules
            .slice()
            .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
            .map((spec) => {
              ruleSeq += 1;
              return {
                id: `r${ruleSeq}`,
                operation: spec.operation,
                target_field: spec.target_field ?? "",
                params: spec.params ?? {},
              };
            })
        );
      } catch (err) {
        // No saved rule set yet for this sheet — start from an empty builder.
        if (!(err instanceof ApiError && err.status === 404)) {
          setError(err instanceof ApiError ? err.message : "Failed to load saved rules.");
        }
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

  async function onSave(draft = false) {
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const res = await api.saveSheetRuleSet(sheetId, rules.map(toSpec), draft);
      setRuleSetVersion(res.version);
      setNotice(
        draft
          ? `Saved as draft (v${res.version}). Publish it from Configs to apply it to the pipeline.`
          : `Saved rule set (v${res.version}, ${res.rules.length} rule(s)). ` +
              "Reused automatically by any file with these same columns."
      );
      toast.success(draft ? `Saved draft v${res.version}.` : `Saved rule set v${res.version}.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Save failed.");
      toast.error("Could not save the rule set.");
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
        description={
          ruleSetVersion
            ? `Loaded saved rule set v${ruleSetVersion}. Add rules by picking a column and an operation. Preview updates live; no JSON required.`
            : "Add rules by picking a column and an operation. Preview updates live; no JSON required."
        }
        actions={
          <>
            <Button variant="outline" onClick={onSuggestAi} disabled={aiLoading}>
              <Sparkles className="h-4 w-4" />
              {aiLoading ? "Thinking…" : "Suggest with AI"}
            </Button>
            <Button variant="outline" onClick={() => setRules((r) => [...r, newRule()])}>
              <Plus className="h-4 w-4" /> Add rule
            </Button>
            <Button
              variant="outline"
              onClick={() => onSave(true)}
              disabled={saving || rules.length === 0}
            >
              Save as draft
            </Button>
            <Button onClick={() => onSave(false)} disabled={saving || rules.length === 0}>
              <Save className="h-4 w-4" />
              {saving ? "Saving…" : "Save & publish"}
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
            {aiSuggestions.length > 0 ? (
              <div className="space-y-2 rounded-lg border border-primary/30 bg-primary/5 p-3">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <Sparkles className="h-4 w-4 text-primary" /> AI suggestions
                </div>
                {aiSuggestions.map((s) => {
                  const p = s.payload as { operation?: string; target_field?: string };
                  return (
                    <div key={s.id} className="flex flex-wrap items-center gap-2 text-sm">
                      <span className="font-mono text-xs">
                        {String(p.operation)}
                        {p.target_field ? ` · ${p.target_field}` : ""}
                      </span>
                      {s.confidence != null ? (
                        <span className="text-xs text-muted-foreground">
                          {Math.round(s.confidence * 100)}%
                        </span>
                      ) : null}
                      {s.rationale ? (
                        <span className="min-w-0 truncate text-xs text-muted-foreground">
                          {s.rationale}
                        </span>
                      ) : null}
                      <div className="ml-auto flex gap-1">
                        <Button size="sm" variant="outline" onClick={() => addSuggestion(s)}>
                          Add
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => dismissSuggestion(s.id)}>
                          Dismiss
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : null}
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

          <div className="space-y-2">
            <h2 className="text-sm font-semibold">Live preview</h2>
            {rows.length === 0 ? (
              <EmptyState
                title="No sample data"
                description="This sheet has no profiled sample values to preview against."
              />
            ) : previewError ? (
              <ErrorBanner message={previewError} />
            ) : (
              <CompactPreview preview={preview} sampleRows={rows} />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

const MAX_PREVIEW_ROWS = 8;

function fmtCell(value: unknown): React.ReactNode {
  return value === null || value === undefined || value === "" ? (
    <span className="text-muted-foreground">—</span>
  ) : (
    String(value)
  );
}

/**
 * Compact single-table preview: shows the *after* result densely with a faint
 * row-hover highlight and a sticky header. When the rule set preserves row count
 * (cell-level ops), changed cells are highlighted and hovering one shows its prior
 * value; row-count-changing ops (dedupe/aggregate/reshape) show a before→after count.
 */
function CompactPreview({
  preview,
  sampleRows,
}: {
  preview: PreviewResponse | null;
  sampleRows: Record<string, unknown>[];
}) {
  const before = preview?.before ?? sampleRows;
  const after = preview?.after ?? sampleRows;
  const cols = Array.from(new Set(after.flatMap((r) => Object.keys(r))));
  const aligned = before.length === after.length; // 1:1 rows → cell diffs are meaningful
  const shown = Math.min(after.length, MAX_PREVIEW_ROWS);

  return (
    <div className="space-y-1.5">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
        <span>
          {aligned ? "Result — changed cells highlighted" : `Rows: ${before.length} → ${after.length}`}
        </span>
        <span>
          showing {shown} of {after.length} sample row{after.length === 1 ? "" : "s"}
        </span>
      </div>
      <div className="max-h-[26rem] overflow-auto rounded-lg border border-border">
        <table className="w-full border-collapse text-sm">
          <thead className="sticky top-0 z-10 bg-muted/70 backdrop-blur">
            <tr>
              {cols.map((c) => (
                <th
                  key={c}
                  className="whitespace-nowrap px-2 py-1.5 text-left text-xs font-medium text-muted-foreground"
                >
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {after.slice(0, shown).map((row, i) => {
              const prev = aligned ? before[i] : undefined;
              return (
                <tr key={i} className="border-t border-border transition-colors hover:bg-muted/40">
                  {cols.map((c) => {
                    const val = row[c];
                    const priorVal = prev?.[c];
                    const changed =
                      aligned && JSON.stringify(priorVal) !== JSON.stringify(val);
                    return (
                      <td
                        key={c}
                        className={cn(
                          "whitespace-nowrap px-2 py-1 tabular-nums",
                          changed && "bg-primary/10"
                        )}
                      >
                        {changed && priorVal !== null && priorVal !== undefined ? (
                          <Tooltip content={`was: ${String(priorVal)}`}>
                            <span>{fmtCell(val)}</span>
                          </Tooltip>
                        ) : (
                          fmtCell(val)
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

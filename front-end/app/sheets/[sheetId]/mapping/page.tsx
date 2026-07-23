"use client";

import { ArrowLeft, Check, CheckCircle2, Save, Sparkles, X } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ErrorBanner, Loading } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
import { CoverageMeter } from "@/components/coverage-meter";
import { SearchableSelect } from "@/components/ui/searchable-select";
import { Table, TD, TH, THead, TR } from "@/components/ui/table";
import { api, ApiError } from "@/lib/api/client";
import type {
  CanonicalFieldRead,
  MappingValidation,
  SheetDetail,
  SuggestionRead,
} from "@/lib/api/types";
import { formatConfidence } from "@/lib/format";

const IGNORE = "__ignore__";
const HIGH_CONFIDENCE = 0.85;

interface SuggestionInfo {
  field: string;
  confidence: number | null;
  rationale: string | null;
}

export default function MappingReviewPage() {
  const { sheetId } = useParams<{ sheetId: string }>();
  const [sheet, setSheet] = useState<SheetDetail | null>(null);
  const [fields, setFields] = useState<CanonicalFieldRead[]>([]);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [suggestions, setSuggestions] = useState<Record<string, SuggestionInfo>>({});
  const [autoApplied, setAutoApplied] = useState(false);
  const [validation, setValidation] = useState<MappingValidation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [suggesting, setSuggesting] = useState(false);
  const [saving, setSaving] = useState(false);

  const columns = useMemo(() => (sheet?.sheet.columns ?? []).map((c) => c.name), [sheet]);

  // Per-column value profile (distinct samples, count, null rate) so users map
  // from real data, not just headers.
  const profileByCol = useMemo(() => {
    const out: Record<string, {
      values: string[];
      distinctCount: number | null;
      distinctCapped: boolean;
      nullRate: number | null;
    }> = {};
    for (const c of sheet?.profile?.column_stats?.columns ?? []) {
      if (!c.name) continue;
      out[c.name] = {
        values: (c.sample_values ?? []).filter((v): v is string => v != null).slice(0, 8),
        distinctCount: c.distinct_count ?? null,
        distinctCapped: Boolean(c.distinct_capped),
        nullRate: c.null_rate ?? null,
      };
    }
    return out;
  }, [sheet]);

  // Canonical-field picker options (used by SearchableSelect).
  const fieldOptions = useMemo(
    () =>
      fields.map((f) => ({
        value: f.name,
        label: f.name,
        hint: `${f.kind}${f.required ? " · required" : ""}`,
      })),
    [fields]
  );

  // Live required-field coverage from the current (unsaved) mapping.
  const coverage = useMemo(() => {
    const required = fields.filter((f) => f.required).map((f) => f.name);
    const targets = new Set(
      Object.values(mapping).filter((v) => v && v !== IGNORE)
    );
    const missing = required.filter((r) => !targets.has(r));
    return { required, coveredCount: required.length - missing.length, missing };
  }, [fields, mapping]);

  const applySuggestions = useCallback((list: SuggestionRead[]) => {
    const next: Record<string, SuggestionInfo> = {};
    for (const s of list) {
      const source = String(s.payload.source_column ?? "");
      const field = String(s.payload.canonical_field ?? "");
      if (source && field)
        next[source] = { field, confidence: s.confidence, rationale: s.rationale };
    }
    setSuggestions(next);
    return next;
  }, []);

  function acceptSuggestion(col: string) {
    const info = suggestions[col];
    if (!info) return;
    setMapping((prev) => ({ ...prev, [col]: info.field }));
  }

  function dismissSuggestion(col: string) {
    setSuggestions((prev) => {
      const copy = { ...prev };
      delete copy[col];
      return copy;
    });
  }

  function acceptAllHighConfidence() {
    setMapping((prev) => {
      const copy = { ...prev };
      for (const [col, info] of Object.entries(suggestions)) {
        if ((info.confidence ?? 0) >= HIGH_CONFIDENCE && !copy[col]) copy[col] = info.field;
      }
      return copy;
    });
  }

  const highConfidenceCount = Object.values(suggestions).filter(
    (i) => (i.confidence ?? 0) >= HIGH_CONFIDENCE
  ).length;

  const load = useCallback(async () => {
    try {
      const [detail, canonical, auto, existing] = await Promise.all([
        api.getSheet(sheetId),
        api.canonicalFields(),
        api.autoMap(sheetId),
        api.listSuggestions(sheetId),
      ]);
      setSheet(detail);
      setFields(canonical.fields);
      applySuggestions(existing);
      if (auto.matched) {
        setAutoApplied(true);
        const seeded: Record<string, string> = {};
        for (const [k, v] of Object.entries(auto.mapping)) seeded[k] = v ?? IGNORE;
        setMapping(seeded);
        setValidation(auto.validation);
      }
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load sheet.");
    }
  }, [sheetId, applySuggestions]);

  useEffect(() => {
    void load();
  }, [load]);

  async function onSuggest() {
    setSuggesting(true);
    setError(null);
    setNotice(null);
    try {
      const res = await api.suggestMapping(sheetId);
      applySuggestions(res.suggestions);
      setNotice(
        "AI proposals ready — review and accept (or “Accept all high-confidence”), then Save."
      );
    } catch (err) {
      if (err instanceof ApiError && err.isLlmDisabled) {
        setError("AI is disabled on the server. You can still map columns manually.");
      } else {
        setError(err instanceof ApiError ? err.message : "Suggestion request failed.");
      }
    } finally {
      setSuggesting(false);
    }
  }

  async function onSave() {
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const payload: Record<string, string | null> = {};
      for (const col of columns) {
        const v = mapping[col];
        payload[col] = v && v !== IGNORE ? v : null;
      }
      const res = await api.saveMapping(sheetId, `mapping v${Date.now()}`, payload);
      setValidation(res.validation);
      setAutoApplied(false);
      setNotice(`Saved mapping (config v${res.config.version}).`);
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
        eyebrow="Mapping review"
        title={sheet?.sheet.sheet_name ?? "Sheet mapping"}
        description="Map each source column to a canonical field. AI can suggest; you decide."
        actions={
          <>
            <Button variant="outline" onClick={onSuggest} disabled={suggesting || !sheet}>
              <Sparkles className="h-4 w-4" />
              {suggesting ? "Thinking…" : "Suggest with AI"}
            </Button>
            <Button
              variant="outline"
              onClick={acceptAllHighConfidence}
              disabled={highConfidenceCount === 0}
              title="Apply every AI proposal with confidence ≥ 85%"
            >
              <Check className="h-4 w-4" />
              Accept {highConfidenceCount > 0 ? `${highConfidenceCount} high-conf` : "high-conf"}
            </Button>
            <Button onClick={onSave} disabled={saving || !sheet}>
              <Save className="h-4 w-4" />
              {saving ? "Saving…" : "Save mapping"}
            </Button>
          </>
        }
      />

      <CoverageMeter
        required={coverage.required}
        coveredCount={coverage.coveredCount}
        missing={coverage.missing}
      />

      {autoApplied ? (
        <div className="flex items-center gap-2 rounded-md border border-primary/30 bg-primary/10 px-3 py-2 text-sm text-primary">
          <CheckCircle2 className="h-4 w-4" />A saved config auto-applied by column signature.
          Confirm or adjust below.
        </div>
      ) : null}
      {notice ? (
        <div className="rounded-md border border-success/30 bg-success/10 px-3 py-2 text-sm text-success">
          {notice}
        </div>
      ) : null}
      {error ? <ErrorBanner message={error} /> : null}
      {validation && !validation.is_complete ? (
        <ErrorBanner
          message={`Missing required field(s): ${validation.missing_required.join(", ") || "—"}`}
        />
      ) : null}
      {validation?.is_complete ? (
        <div className="rounded-md border border-success/30 bg-success/10 px-3 py-2 text-sm text-success">
          Mapping is complete — all required fields are covered.
        </div>
      ) : null}

      {sheet === null ? (
        <Loading label="Loading columns…" />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Source column</TH>
              <TH>Type</TH>
              <TH>Values (profile)</TH>
              <TH>AI suggestion</TH>
              <TH>Canonical field</TH>
            </TR>
          </THead>
          <tbody>
            {sheet.sheet.columns.map((col) => {
              const suggestion = suggestions[col.name];
              const prof = profileByCol[col.name];
              const applied = Boolean(suggestion && mapping[col.name] === suggestion.field);
              return (
                <TR key={col.index}>
                  <TD className="font-medium">{col.name}</TD>
                  <TD>
                    <Badge variant="outline">{col.type}</Badge>
                  </TD>
                  <TD className="max-w-[22rem]">
                    <div className="flex flex-wrap gap-1">
                      {(prof?.values ?? []).map((v, i) => (
                        <span
                          key={`${col.name}-${i}`}
                          className="rounded bg-muted px-1.5 py-0.5 text-[11px] tabular-nums"
                        >
                          {v}
                        </span>
                      ))}
                      {prof && prof.values.length === 0 ? (
                        <span className="text-xs text-muted-foreground">—</span>
                      ) : null}
                    </div>
                    <div className="mt-1 text-[11px] text-muted-foreground">
                      {prof?.distinctCount != null
                        ? `${prof.distinctCount} distinct${prof.distinctCapped ? "+" : ""}`
                        : null}
                      {prof?.nullRate
                        ? ` · ${Math.round((prof.nullRate ?? 0) * 100)}% null`
                        : null}
                    </div>
                  </TD>
                  <TD>
                    {suggestion ? (
                      <div className="flex flex-col gap-1" title={suggestion.rationale ?? ""}>
                        <div className="flex items-center gap-1.5">
                          <Badge variant={applied ? "default" : "outline"}>
                            {suggestion.field}
                          </Badge>
                          <span className="text-[11px] tabular-nums text-muted-foreground">
                            {formatConfidence(suggestion.confidence)}
                          </span>
                        </div>
                        {applied ? (
                          <span className="inline-flex items-center gap-1 text-[11px] text-success">
                            <Check className="h-3 w-3" /> applied
                          </span>
                        ) : (
                          <div className="flex gap-1">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => acceptSuggestion(col.name)}
                            >
                              <Check className="h-3 w-3" /> Accept
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => dismissSuggestion(col.name)}
                              aria-label="Dismiss suggestion"
                            >
                              <X className="h-3 w-3" />
                            </Button>
                          </div>
                        )}
                      </div>
                    ) : (
                      <span className="text-xs text-muted-foreground">—</span>
                    )}
                  </TD>
                  <TD>
                    <SearchableSelect
                      value={mapping[col.name] ?? ""}
                      options={[
                        { value: IGNORE, label: "Ignore this column", hint: "drop" },
                        ...fieldOptions,
                      ]}
                      onChange={(v) =>
                        setMapping((prev) => ({ ...prev, [col.name]: v }))
                      }
                    />
                  </TD>
                </TR>
              );
            })}
          </tbody>
        </Table>
      )}
    </div>
  );
}

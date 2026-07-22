"use client";

import { ArrowLeft, CheckCircle2, Save, Sparkles } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ErrorBanner, Loading } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
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
  const samplesByCol = useMemo(() => {
    const out: Record<string, (string | null)[]> = {};
    for (const c of sheet?.profile?.column_stats?.columns ?? []) {
      if (c.name) out[c.name] = (c.sample_values ?? []).slice(0, 3);
    }
    return out;
  }, [sheet]);

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
      const next = applySuggestions(res.suggestions);
      // Pre-fill any unset columns with the suggested field.
      setMapping((prev) => {
        const copy = { ...prev };
        for (const [source, info] of Object.entries(next)) {
          if (!copy[source]) copy[source] = info.field;
        }
        return copy;
      });
      setNotice("AI suggestions applied — review, then Save mapping to commit.");
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
            <Button onClick={onSave} disabled={saving || !sheet}>
              <Save className="h-4 w-4" />
              {saving ? "Saving…" : "Save mapping"}
            </Button>
          </>
        }
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
              <TH>Samples</TH>
              <TH>AI suggestion</TH>
              <TH>Canonical field</TH>
            </TR>
          </THead>
          <tbody>
            {sheet.sheet.columns.map((col) => {
              const suggestion = suggestions[col.name];
              return (
                <TR key={col.index}>
                  <TD className="font-medium">{col.name}</TD>
                  <TD>
                    <Badge variant="outline">{col.type}</Badge>
                  </TD>
                  <TD
                    className="max-w-[16rem] truncate text-muted-foreground"
                    title={(samplesByCol[col.name] ?? []).join(", ")}
                  >
                    {(samplesByCol[col.name] ?? []).filter(Boolean).join(", ") || "—"}
                  </TD>
                  <TD>
                    {suggestion ? (
                      <span
                        className="inline-flex items-center gap-2"
                        title={suggestion.rationale ?? ""}
                      >
                        <Badge variant="default">{suggestion.field}</Badge>
                        <span className="text-xs tabular-nums text-muted-foreground">
                          {formatConfidence(suggestion.confidence)}
                        </span>
                      </span>
                    ) : (
                      <span className="text-xs text-muted-foreground">—</span>
                    )}
                  </TD>
                  <TD>
                    <select
                      value={mapping[col.name] ?? ""}
                      onChange={(e) =>
                        setMapping((prev) => ({ ...prev, [col.name]: e.target.value }))
                      }
                      className="h-8 w-full rounded-md border border-input bg-background px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <option value="">— select —</option>
                      <option value={IGNORE}>Ignore this column</option>
                      {fields.map((f) => (
                        <option key={f.name} value={f.name}>
                          {f.name}
                          {f.required ? " (required)" : ""}
                        </option>
                      ))}
                    </select>
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

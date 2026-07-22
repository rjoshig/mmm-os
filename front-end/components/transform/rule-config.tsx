"use client";

import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";

export interface UiRule {
  id: string;
  operation: string;
  target_field: string;
  params: Record<string, unknown>;
}

export const OPERATIONS: { value: string; label: string; hint: string }[] = [
  { value: "normalize_text", label: "Normalize text", hint: "Trim / case / collapse spaces" },
  { value: "map_value", label: "Map values", hint: "Collapse raw values to canonical terms" },
  { value: "fill_missing", label: "Fill missing", hint: "Replace empty cells with a value" },
  { value: "rename_column", label: "Rename column", hint: "Rename a source column" },
  { value: "cast_type", label: "Cast type", hint: "number / string / boolean" },
  { value: "parse_date", label: "Parse date", hint: "Normalize to ISO date" },
];

const inputCls =
  "h-8 rounded-md border border-input bg-background px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

/** Per-operation configuration form. Emits typed params — no raw JSON exposed. */
export function RuleConfig({
  rule,
  columns,
  onChange,
  onRemove,
}: {
  rule: UiRule;
  columns: string[];
  onChange: (next: UiRule) => void;
  onRemove: () => void;
}) {
  function setParams(p: Record<string, unknown>) {
    onChange({ ...rule, params: { ...rule.params, ...p } });
  }

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={rule.operation}
          onChange={(e) => onChange({ ...rule, operation: e.target.value, params: {} })}
          className={inputCls}
        >
          {OPERATIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>

        <span className="text-xs text-muted-foreground">on</span>
        <select
          value={rule.target_field}
          onChange={(e) => onChange({ ...rule, target_field: e.target.value })}
          className={inputCls}
        >
          <option value="">— column —</option>
          {columns.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>

        <Button variant="ghost" size="sm" className="ml-auto" onClick={onRemove}>
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>

      <div className="mt-3">
        {rule.operation === "normalize_text" ? (
          <div className="flex flex-wrap gap-3 text-sm">
            {(["strip", "collapse_ws", "lower", "upper"] as const).map((k) => (
              <label key={k} className="inline-flex items-center gap-1.5">
                <input
                  type="checkbox"
                  checked={Boolean(rule.params[k] ?? k === "strip")}
                  onChange={(e) => setParams({ [k]: e.target.checked })}
                />
                {k}
              </label>
            ))}
          </div>
        ) : null}

        {rule.operation === "map_value" ? (
          <MapValueEditor
            mapping={(rule.params.mapping as Record<string, string>) ?? {}}
            onChange={(mapping) => setParams({ mapping })}
          />
        ) : null}

        {rule.operation === "fill_missing" ? (
          <input
            className={`${inputCls} w-64`}
            placeholder="Value to fill (e.g. 0 or Unknown)"
            value={String(rule.params.value ?? "")}
            onChange={(e) => setParams({ value: e.target.value })}
          />
        ) : null}

        {rule.operation === "rename_column" ? (
          <input
            className={`${inputCls} w-64`}
            placeholder="New column name"
            value={String(rule.params.to ?? "")}
            onChange={(e) => setParams({ to: e.target.value })}
          />
        ) : null}

        {rule.operation === "cast_type" ? (
          <select
            className={inputCls}
            value={String(rule.params.to ?? "number")}
            onChange={(e) => setParams({ to: e.target.value })}
          >
            <option value="number">number</option>
            <option value="string">string</option>
            <option value="boolean">boolean</option>
          </select>
        ) : null}

        {rule.operation === "parse_date" ? (
          <input
            className={`${inputCls} w-48`}
            placeholder="Output format (%Y-%m-%d)"
            value={String(rule.params.output ?? "%Y-%m-%d")}
            onChange={(e) => setParams({ output: e.target.value })}
          />
        ) : null}
      </div>
    </div>
  );
}

function MapValueEditor({
  mapping,
  onChange,
}: {
  mapping: Record<string, string>;
  onChange: (m: Record<string, string>) => void;
}) {
  const pairs = Object.entries(mapping);
  const rows = pairs.length ? pairs : [["", ""]];

  function update(index: number, from: string, to: string) {
    const next: Record<string, string> = {};
    rows.forEach(([f, t], i) => {
      const kf = i === index ? from : f;
      const kt = i === index ? to : t;
      if (kf) next[kf] = kt;
    });
    onChange(next);
  }

  return (
    <div className="space-y-2">
      {rows.map(([from, to], i) => (
        <div key={i} className="flex items-center gap-2 text-sm">
          <input
            className={`${inputCls} w-40`}
            placeholder="raw value"
            value={from}
            onChange={(e) => update(i, e.target.value, to)}
          />
          <span className="text-muted-foreground">→</span>
          <input
            className={`${inputCls} w-40`}
            placeholder="canonical"
            value={to}
            onChange={(e) => update(i, from, e.target.value)}
          />
        </div>
      ))}
      <button
        type="button"
        className="text-xs text-primary hover:underline"
        onClick={() => onChange({ ...mapping, "": "" })}
      >
        + add mapping
      </button>
    </div>
  );
}

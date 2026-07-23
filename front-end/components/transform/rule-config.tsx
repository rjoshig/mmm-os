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
  {
    value: "convert_currency",
    label: "Convert currency",
    hint: "FX rate, or normalize to the reporting currency",
  },
  {
    value: "normalize_timezone",
    label: "Normalize timezone",
    hint: "Convert a timestamp to the reporting timezone",
  },
  { value: "dedupe", label: "Deduplicate rows", hint: "Drop duplicate rows (by key or whole row)" },
  { value: "reshape", label: "Reshape wide → long", hint: "Unpivot columns into rows" },
  {
    value: "aggregate",
    label: "Aggregate to weekly/monthly",
    hint: "Roll daily rows up to the MMM modelling grain",
  },
  { value: "custom", label: "Custom expression", hint: "Compute a field from an expression" },
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

        {rule.operation === "convert_currency" ? (
          <div className="space-y-2">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={Boolean(rule.params.to_reporting)}
                onChange={(e) =>
                  setParams({
                    to_reporting: e.target.checked || undefined,
                    rate: e.target.checked ? undefined : rule.params.rate,
                  })
                }
              />
              Normalize to the reporting currency (uses Settings → FX rates)
            </label>
            {rule.params.to_reporting ? (
              <label className="flex flex-wrap items-center gap-2 text-sm">
                <span className="text-muted-foreground">Source-currency column</span>
                <select
                  className={inputCls}
                  value={String(rule.params.currency_field ?? "")}
                  onChange={(e) => setParams({ currency_field: e.target.value || undefined })}
                >
                  <option value="">— column —</option>
                  {columns.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              <label className="flex items-center gap-2 text-sm">
                <span className="text-muted-foreground">Fixed rate (multiplier)</span>
                <input
                  className={`${inputCls} w-32`}
                  type="number"
                  step="any"
                  placeholder="e.g. 1.08"
                  value={rule.params.rate == null ? "" : String(rule.params.rate)}
                  onChange={(e) =>
                    setParams({ rate: e.target.value === "" ? undefined : Number(e.target.value) })
                  }
                />
              </label>
            )}
            <p className="text-xs text-muted-foreground">
              {rule.params.to_reporting
                ? "Each row's value is converted from its source currency into the tenant reporting currency."
                : "Multiplies the selected numeric column by this fixed rate."}
            </p>
          </div>
        ) : null}

        {rule.operation === "normalize_timezone" ? (
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="text-muted-foreground">from</span>
              <input
                className={`${inputCls} w-44`}
                placeholder="UTC"
                value={String(rule.params.from_tz ?? "UTC")}
                onChange={(e) => setParams({ from_tz: e.target.value })}
              />
              <span className="text-muted-foreground">→ reporting timezone</span>
              <label className="inline-flex items-center gap-1.5">
                <input
                  type="checkbox"
                  checked={Boolean(rule.params.to_date)}
                  onChange={(e) => setParams({ to_date: e.target.checked || undefined })}
                />
                also set date
              </label>
            </div>
            <p className="text-xs text-muted-foreground">
              Converts the selected timestamp column to the reporting timezone (Settings). With
              &ldquo;also set date&rdquo;, the daily bucket is taken in the reporting frame.
            </p>
          </div>
        ) : null}

        {rule.operation === "dedupe" ? (
          <div className="space-y-1.5">
            <p className="text-xs text-muted-foreground">
              Key columns (none = dedupe by the whole row):
            </p>
            <ColumnChecklist
              columns={columns}
              selected={(rule.params.keys as string[]) ?? []}
              onChange={(keys) => setParams({ keys: keys.length ? keys : undefined })}
            />
          </div>
        ) : null}

        {rule.operation === "reshape" ? (
          <div className="space-y-2">
            <div>
              <p className="mb-1 text-xs text-muted-foreground">Keep per row (id columns):</p>
              <ColumnChecklist
                columns={columns}
                selected={(rule.params.id_vars as string[]) ?? []}
                onChange={(id_vars) => setParams({ id_vars })}
              />
            </div>
            <div>
              <p className="mb-1 text-xs text-muted-foreground">Unpivot (value columns):</p>
              <ColumnChecklist
                columns={columns}
                selected={(rule.params.value_vars as string[]) ?? []}
                onChange={(value_vars) => setParams({ value_vars })}
              />
            </div>
            <div className="flex flex-wrap gap-2 text-sm">
              <input
                className={`${inputCls} w-40`}
                placeholder="dimension name (var_name)"
                value={String(rule.params.var_name ?? "")}
                onChange={(e) => setParams({ var_name: e.target.value })}
              />
              <input
                className={`${inputCls} w-40`}
                placeholder="measure name (value_name)"
                value={String(rule.params.value_name ?? "")}
                onChange={(e) => setParams({ value_name: e.target.value })}
              />
            </div>
          </div>
        ) : null}

        {rule.operation === "aggregate" ? (
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="text-muted-foreground">Grain</span>
              <select
                className={inputCls}
                value={String(rule.params.freq ?? "weekly")}
                onChange={(e) => setParams({ freq: e.target.value })}
              >
                <option value="weekly">weekly</option>
                <option value="monthly">monthly</option>
              </select>
              {String(rule.params.freq ?? "weekly") === "weekly" ? (
                <>
                  <span className="text-muted-foreground">week starts</span>
                  <select
                    className={inputCls}
                    value={String(rule.params.week_start ?? "monday")}
                    onChange={(e) => setParams({ week_start: e.target.value })}
                  >
                    <option value="monday">Monday</option>
                    <option value="sunday">Sunday</option>
                  </select>
                </>
              ) : null}
              <label className="inline-flex items-center gap-1.5">
                <input
                  type="checkbox"
                  checked={rule.params.fill_gaps !== false}
                  onChange={(e) => setParams({ fill_gaps: e.target.checked })}
                />
                fill gaps (continuous series)
              </label>
            </div>
            <p className="text-xs text-muted-foreground">
              Uses the canonical schema: measures are summed, numeric factors averaged, and
              dimensions (channel, geo…) kept as grouping keys. The target column is ignored.
            </p>
          </div>
        ) : null}

        {rule.operation === "custom" ? (
          <div className="space-y-1.5">
            <input
              className={`${inputCls} w-full`}
              placeholder="Expression, e.g. spend / impressions * 1000"
              value={String(rule.params.expression ?? "")}
              onChange={(e) => setParams({ expression: e.target.value })}
            />
            <input
              className={`${inputCls} w-64`}
              placeholder="Output column (defaults to the selected column)"
              value={String(rule.params.output ?? "")}
              onChange={(e) => setParams({ output: e.target.value || undefined })}
            />
            <p className="text-xs text-muted-foreground">
              Column names are the variables; a sandboxed expression is evaluated per row.
            </p>
          </div>
        ) : null}
      </div>
    </div>
  );
}

/** A compact set of column checkboxes for list-valued params (keys / id_vars / value_vars). */
function ColumnChecklist({
  columns,
  selected,
  onChange,
}: {
  columns: string[];
  selected: string[];
  onChange: (next: string[]) => void;
}) {
  if (columns.length === 0) {
    return <p className="text-xs text-muted-foreground">No columns detected on this sheet.</p>;
  }
  function toggle(col: string, on: boolean) {
    onChange(on ? [...selected, col] : selected.filter((c) => c !== col));
  }
  return (
    <div className="flex flex-wrap gap-x-3 gap-y-1.5 text-sm">
      {columns.map((col) => (
        <label key={col} className="inline-flex items-center gap-1.5">
          <input
            type="checkbox"
            checked={selected.includes(col)}
            onChange={(e) => toggle(col, e.target.checked)}
          />
          {col}
        </label>
      ))}
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

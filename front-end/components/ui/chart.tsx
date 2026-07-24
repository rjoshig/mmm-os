"use client";

// Theme-aware chart primitives built on Recharts (Cycle 5, Phase 17/20).
//
// Colors reference the design-system HSL CSS variables (e.g. hsl(var(--primary)))
// so every chart tracks light/dark automatically — never hardcode hex.

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { cn } from "@/lib/utils";

/** A design-system token usable as an SVG color, e.g. token("primary"). */
export function token(name: string): string {
  return `hsl(var(--${name}))`;
}

const AXIS = { fontSize: 11, fill: token("muted-foreground") };

export interface BarDatum {
  label: string;
  value: number;
  /** Optional per-bar color token (defaults to primary). */
  color?: string;
}

/** A compact, theme-aware vertical bar chart for categorical counts. */
export function SimpleBarChart({
  data,
  height = 200,
  className,
  valueLabel,
}: {
  data: BarDatum[];
  height?: number;
  className?: string;
  valueLabel?: string;
}) {
  return (
    <div className={cn("w-full", className)} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 4, left: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={token("border")} vertical={false} />
          <XAxis dataKey="label" tick={AXIS} tickLine={false} axisLine={{ stroke: token("border") }} />
          <YAxis tick={AXIS} tickLine={false} axisLine={false} width={36} allowDecimals={false} />
          <Tooltip
            cursor={{ fill: token("muted") }}
            contentStyle={{
              background: token("card"),
              border: `1px solid ${token("border")}`,
              borderRadius: 8,
              fontSize: 12,
              color: token("foreground"),
            }}
            labelStyle={{ color: token("foreground") }}
            formatter={(value) => [value, valueLabel ?? "value"]}
          />
          <Bar dataKey="value" radius={[4, 4, 0, 0]} maxBarSize={48}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.color ?? token("primary")} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** A tiny inline bar row (no axes) for compact distributions. */
export function MiniBars({ data, className }: { data: BarDatum[]; className?: string }) {
  const max = Math.max(1, ...data.map((d) => d.value));
  return (
    <div className={cn("space-y-1.5", className)}>
      {data.map((d) => (
        <div key={d.label} className="flex items-center gap-2 text-xs">
          <span className="w-28 shrink-0 truncate text-muted-foreground" title={d.label}>
            {d.label}
          </span>
          <span className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
            <span
              className="block h-full rounded-full"
              style={{ width: `${(d.value / max) * 100}%`, background: d.color ?? token("primary") }}
            />
          </span>
          <span className="w-10 text-right tabular-nums">{d.value}</span>
        </div>
      ))}
    </div>
  );
}

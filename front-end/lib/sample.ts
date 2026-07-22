import type { SheetDetail } from "@/lib/api/types";

/**
 * Build sample rows from a sheet's profile (column sample values), zipped by
 * position into row objects keyed by column name. Used to seed the transform
 * preview and validation screens with real-ish data.
 *
 * NOTE (interim): the backend exposes per-column *sample values* via the profile,
 * not full stored rows. These zipped rows are representative, not the exact
 * source rows. A dedicated "sheet sample rows" endpoint would make preview exact.
 */
export function sampleRowsFromProfile(detail: SheetDetail, limit = 8): Record<string, unknown>[] {
  const cols = (detail.profile?.column_stats?.columns ?? []).filter((c) => c.name);
  if (cols.length === 0) return [];
  const maxLen = cols.reduce((n, c) => Math.max(n, c.sample_values?.length ?? 0), 0);
  const count = Math.min(limit, maxLen);
  const rows: Record<string, unknown>[] = [];
  for (let i = 0; i < count; i += 1) {
    const row: Record<string, unknown> = {};
    for (const c of cols) row[c.name] = c.sample_values?.[i] ?? null;
    rows.push(row);
  }
  return rows;
}

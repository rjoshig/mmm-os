"use client";

import { ArrowDown, ArrowUp, ChevronDown, ChevronRight, Search } from "lucide-react";
import { Fragment, useMemo, useState } from "react";
import { EmptyState } from "@/components/ui/feedback";
import { cn } from "@/lib/utils";

export interface DataColumn<T> {
  /** Stable column id. */
  key: string;
  header: string;
  /** Cell renderer. */
  cell: (row: T) => React.ReactNode;
  /** Provide to make the column sortable. */
  sortKey?: (row: T) => string | number | null;
  align?: "left" | "right";
  headerClassName?: string;
  cellClassName?: string;
}

/**
 * Reusable client-side data table (enterprise-table UX best practices): global
 * search, sortable columns, pagination with rows-per-page + "showing x–y of N",
 * density toggle, sticky header, row hover, optional per-row expansion, and a
 * toolbar slot for domain filters. Filter/sort/search reset to page 1.
 * Client-side only (best for <1000 rows) — pass pre-filtered rows for larger sets.
 */
export function DataTable<T>({
  rows,
  columns,
  rowKey,
  search,
  searchPlaceholder = "Search…",
  pageSize = 10,
  emptyTitle = "Nothing here",
  emptyDescription,
  expandable,
  initialSort,
  toolbar,
}: {
  rows: T[];
  columns: DataColumn<T>[];
  rowKey: (row: T) => string;
  /** Enables the search box; returns the searchable text for a row. */
  search?: (row: T) => string;
  searchPlaceholder?: string;
  pageSize?: number;
  emptyTitle?: string;
  emptyDescription?: string;
  /** Enables per-row expansion; return null for a non-expandable row. */
  expandable?: (row: T) => React.ReactNode | null;
  initialSort?: { key: string; dir: "asc" | "desc" };
  toolbar?: React.ReactNode;
}) {
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<{ key: string; dir: "asc" | "desc" } | null>(initialSort ?? null);
  const [page, setPage] = useState(0);
  const [perPage, setPerPage] = useState(pageSize);
  const [dense, setDense] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q || !search) return rows;
    return rows.filter((r) => search(r).toLowerCase().includes(q));
  }, [rows, query, search]);

  const sorted = useMemo(() => {
    if (!sort) return filtered;
    const col = columns.find((c) => c.key === sort.key);
    if (!col?.sortKey) return filtered;
    const dir = sort.dir === "asc" ? 1 : -1;
    return [...filtered].sort((a, b) => {
      const av = col.sortKey!(a);
      const bv = col.sortKey!(b);
      if (av === bv) return 0;
      if (av === null) return 1;
      if (bv === null) return -1;
      return av < bv ? -dir : dir;
    });
  }, [filtered, sort, columns]);

  const total = sorted.length;
  const pageCount = Math.max(1, Math.ceil(total / perPage));
  const safePage = Math.min(page, pageCount - 1);
  const start = safePage * perPage;
  const pageRows = sorted.slice(start, start + perPage);

  function toggleSort(key: string) {
    setPage(0);
    setSort((s) =>
      s?.key === key ? { key, dir: s.dir === "asc" ? "desc" : "asc" } : { key, dir: "asc" }
    );
  }

  const cellPad = dense ? "px-2 py-1.5" : "px-3 py-2.5";

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        {search ? (
          <div className="flex h-8 items-center gap-1.5 rounded-md border border-input bg-background px-2">
            <Search className="h-3.5 w-3.5 text-muted-foreground" />
            <input
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(0);
              }}
              placeholder={searchPlaceholder}
              className="h-full w-44 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
          </div>
        ) : null}
        {toolbar}
        <button
          type="button"
          onClick={() => setDense((d) => !d)}
          className="ml-auto rounded-md border border-border px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
        >
          {dense ? "Comfortable" : "Compact"}
        </button>
      </div>

      {total === 0 ? (
        <EmptyState title={emptyTitle} description={emptyDescription} />
      ) : (
        <>
          <div className="max-h-[34rem] overflow-auto rounded-lg border border-border">
            <table className="w-full border-collapse text-sm">
              <thead className="sticky top-0 z-10 bg-muted/70 backdrop-blur">
                <tr>
                  {expandable ? <th className="w-6" /> : null}
                  {columns.map((c) => (
                    <th
                      key={c.key}
                      className={cn(
                        "whitespace-nowrap px-2 py-1.5 text-xs font-medium text-muted-foreground",
                        c.align === "right" ? "text-right" : "text-left",
                        c.sortKey && "cursor-pointer select-none hover:text-foreground",
                        c.headerClassName
                      )}
                      onClick={c.sortKey ? () => toggleSort(c.key) : undefined}
                    >
                      <span className="inline-flex items-center gap-1">
                        {c.header}
                        {sort?.key === c.key ? (
                          sort.dir === "asc" ? (
                            <ArrowUp className="h-3 w-3" />
                          ) : (
                            <ArrowDown className="h-3 w-3" />
                          )
                        ) : null}
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pageRows.map((row) => {
                  const key = rowKey(row);
                  const expandContent = expandable?.(row) ?? null;
                  const isOpen = expanded === key;
                  return (
                    <Fragment key={key}>
                      <tr
                        className={cn(
                          "border-t border-border transition-colors hover:bg-muted/40",
                          expandContent && "cursor-pointer"
                        )}
                        onClick={
                          expandContent ? () => setExpanded(isOpen ? null : key) : undefined
                        }
                      >
                        {expandable ? (
                          <td className="pl-2 text-muted-foreground">
                            {expandContent ? (
                              isOpen ? (
                                <ChevronDown className="h-4 w-4" />
                              ) : (
                                <ChevronRight className="h-4 w-4" />
                              )
                            ) : null}
                          </td>
                        ) : null}
                        {columns.map((c) => (
                          <td
                            key={c.key}
                            className={cn(
                              cellPad,
                              "align-middle",
                              c.align === "right" ? "text-right tabular-nums" : "text-left",
                              c.cellClassName
                            )}
                          >
                            {c.cell(row)}
                          </td>
                        ))}
                      </tr>
                      {isOpen && expandContent ? (
                        <tr className="border-t border-border bg-muted/20">
                          <td colSpan={columns.length + (expandable ? 1 : 0)} className="p-3">
                            {expandContent}
                          </td>
                        </tr>
                      ) : null}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
            <span>
              Showing {start + 1}–{Math.min(start + perPage, total)} of {total}
              {search && query ? ` (filtered from ${rows.length})` : ""}
            </span>
            <div className="flex items-center gap-2">
              <label className="flex items-center gap-1">
                Rows
                <select
                  value={perPage}
                  onChange={(e) => {
                    setPerPage(Number(e.target.value));
                    setPage(0);
                  }}
                  className="h-7 rounded-md border border-input bg-background px-1 text-xs"
                >
                  {[10, 25, 50, 100].map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                disabled={safePage === 0}
                onClick={() => setPage(safePage - 1)}
                className="rounded-md border border-border px-2 py-1 disabled:opacity-40"
              >
                Prev
              </button>
              <span className="tabular-nums">
                {safePage + 1}/{pageCount}
              </span>
              <button
                type="button"
                disabled={safePage >= pageCount - 1}
                onClick={() => setPage(safePage + 1)}
                className="rounded-md border border-border px-2 py-1 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

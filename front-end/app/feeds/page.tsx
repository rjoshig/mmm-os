"use client";

import { Copy, FileStack, Plus, Trash2, Upload } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { CloneDialog } from "@/components/clone-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataTable, type DataColumn } from "@/components/ui/data-table";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState, ErrorBanner } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
import { TableSkeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api/client";
import type { FeedTemplate, FeedTemplatePreview, FixedField } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";

const inputCls =
  "h-9 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

export default function FeedsPage() {
  const toast = useToast();
  const [templates, setTemplates] = useState<FeedTemplate[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [previewFor, setPreviewFor] = useState<FeedTemplate | null>(null);
  const [cloneFor, setCloneFor] = useState<FeedTemplate | null>(null);

  const load = useCallback(async () => {
    try {
      setTemplates(await api.listFeedTemplates());
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load feed templates.");
      setTemplates([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function remove(t: FeedTemplate) {
    try {
      await api.deleteFeedTemplate(t.id);
      toast.success(`Removed "${t.name}".`);
      void load();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not delete the template.");
    }
  }

  const columns: DataColumn<FeedTemplate>[] = [
    {
      key: "name",
      header: "Feed template",
      cell: (t) => <span className="font-medium">{t.name}</span>,
      sortKey: (t) => t.name,
    },
    {
      key: "fmt",
      header: "Format",
      cell: (t) => (
        <Badge variant="secondary">
          {t.fmt === "fixed_width"
            ? "fixed-width"
            : t.fmt === "delimited"
              ? `delimited${t.delimiter ? ` "${t.delimiter}"` : " (sniff)"}`
              : t.fmt}
        </Badge>
      ),
      sortKey: (t) => t.fmt,
    },
    {
      key: "cols",
      header: "Columns",
      align: "right",
      cell: (t) => (
        <span className="tabular-nums text-muted-foreground">
          {t.fmt === "fixed_width" ? t.fixed_fields.length : t.expected_columns.length}
        </span>
      ),
    },
    {
      key: "glob",
      header: "Match",
      cell: (t) => (
        <span className="mono text-xs text-muted-foreground">{t.filename_glob ?? "—"}</span>
      ),
    },
    {
      key: "created",
      header: "Created",
      cell: (t) => <span className="text-muted-foreground">{formatDateTime(t.created_at)}</span>,
      sortKey: (t) => t.created_at,
    },
    {
      key: "actions",
      header: "",
      align: "right",
      cell: (t) => (
        <div className="flex justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={() => setPreviewFor(t)}>
            <Upload className="h-4 w-4" /> Test
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setCloneFor(t)} aria-label="Duplicate">
            <Copy className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="sm" onClick={() => void remove(t)}>
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <NewTemplateDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onCreated={(t) => {
          setDialogOpen(false);
          toast.success(`Feed template "${t.name}" created.`);
          void load();
        }}
      />
      <PreviewDialog template={previewFor} onClose={() => setPreviewFor(null)} />
      {cloneFor && (
        <CloneDialog
          open
          onClose={() => setCloneFor(null)}
          entityLabel="feed template"
          currentName={cloneFor.name}
          onClone={async (opts) => {
            await api.cloneFeedTemplate(cloneFor.id, { new_name: opts.new_name });
            void load();
          }}
        />
      )}
      <PageHeader
        eyebrow="Ingestion"
        title="File feeds"
        description="Define a reusable layout for each recurring file a customer sends (delimited or fixed-width). A matching feed then parses — and auto-maps by column signature — the same way every time."
        actions={
          <Button onClick={() => setDialogOpen(true)}>
            <Plus className="h-4 w-4" /> New feed template
          </Button>
        }
      />

      {error ? <ErrorBanner message={error} /> : null}

      {templates === null ? (
        <TableSkeleton rows={4} cols={5} />
      ) : templates.length === 0 ? (
        <EmptyState
          icon={<FileStack className="h-6 w-6" />}
          title="No feed templates yet"
          description="Create a template for a recurring fixed-width or delimited feed."
          action={
            <Button onClick={() => setDialogOpen(true)}>
              <Plus className="h-4 w-4" /> New feed template
            </Button>
          }
        />
      ) : (
        <DataTable
          rows={templates}
          columns={columns}
          rowKey={(t) => t.id}
          search={(t) => `${t.name} ${t.fmt} ${t.filename_glob ?? ""}`}
          searchPlaceholder="Search feed templates…"
          initialSort={{ key: "created", dir: "desc" }}
        />
      )}
    </div>
  );
}

function NewTemplateDialog({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (t: FeedTemplate) => void;
}) {
  const [name, setName] = useState("");
  const [fmt, setFmt] = useState("delimited");
  const [delimiter, setDelimiter] = useState("");
  const [hasHeader, setHasHeader] = useState(true);
  const [expected, setExpected] = useState("");
  const [glob, setGlob] = useState("");
  const [fields, setFields] = useState<FixedField[]>([{ name: "", start: 0, width: 1 }]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  function setField(i: number, patch: Partial<FixedField>) {
    setFields((fs) => fs.map((f, idx) => (idx === i ? { ...f, ...patch } : f)));
  }

  async function create() {
    setSaving(true);
    setError(null);
    try {
      const cleanFields = fields.filter((f) => f.name.trim());
      const t = await api.createFeedTemplate({
        name: name.trim(),
        fmt,
        delimiter: fmt === "delimited" && delimiter ? delimiter : null,
        has_header: hasHeader,
        fixed_fields: fmt === "fixed_width" ? cleanFields : [],
        expected_columns:
          fmt === "fixed_width"
            ? cleanFields.map((f) => f.name.trim())
            : expected
                .split(",")
                .map((c) => c.trim())
                .filter(Boolean),
        filename_glob: glob.trim() || null,
      });
      onCreated(t);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create the template.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="New feed template"
      description="Describe how this recurring file is laid out."
    >
      <div className="space-y-4">
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">Name</span>
          <input
            className={inputCls}
            placeholder="Daily store sales"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </label>
        <div className="grid grid-cols-2 gap-3">
          <label className="block space-y-1.5">
            <span className="text-sm font-medium">Format</span>
            <select className={inputCls} value={fmt} onChange={(e) => setFmt(e.target.value)}>
              <option value="delimited">Delimited (CSV/TSV/…)</option>
              <option value="fixed_width">Fixed-width</option>
              <option value="xlsx">Excel (.xlsx)</option>
            </select>
          </label>
          <label className="flex items-end gap-2 pb-2 text-sm">
            <input
              type="checkbox"
              checked={hasHeader}
              onChange={(e) => setHasHeader(e.target.checked)}
            />
            <span>File has a header row</span>
          </label>
        </div>

        {fmt === "delimited" ? (
          <>
            <label className="block space-y-1.5">
              <span className="text-sm font-medium">Delimiter (blank = auto-detect)</span>
              <input
                className={inputCls}
                placeholder="e.g. | or ; or \t"
                value={delimiter}
                onChange={(e) => setDelimiter(e.target.value)}
              />
            </label>
            <label className="block space-y-1.5">
              <span className="text-sm font-medium">Expected columns (comma-separated)</span>
              <input
                className={inputCls}
                placeholder="date, store, spend"
                value={expected}
                onChange={(e) => setExpected(e.target.value)}
              />
            </label>
          </>
        ) : null}

        {fmt === "fixed_width" ? (
          <div className="space-y-2">
            <span className="text-sm font-medium">Fixed-width fields</span>
            {fields.map((f, i) => (
              <div key={i} className="grid grid-cols-[1fr_5rem_5rem_2rem] items-center gap-2">
                <input
                  className={inputCls}
                  placeholder="column name"
                  value={f.name}
                  onChange={(e) => setField(i, { name: e.target.value })}
                />
                <input
                  className={inputCls}
                  type="number"
                  min={0}
                  placeholder="start"
                  value={f.start}
                  onChange={(e) => setField(i, { start: Number(e.target.value) })}
                />
                <input
                  className={inputCls}
                  type="number"
                  min={1}
                  placeholder="width"
                  value={f.width}
                  onChange={(e) => setField(i, { width: Number(e.target.value) })}
                />
                <button
                  type="button"
                  className="text-muted-foreground hover:text-destructive"
                  onClick={() => setFields((fs) => fs.filter((_, idx) => idx !== i))}
                  aria-label="Remove field"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setFields((fs) => [...fs, { name: "", start: 0, width: 1 }])}
            >
              <Plus className="h-4 w-4" /> Add field
            </Button>
          </div>
        ) : null}

        <label className="block space-y-1.5">
          <span className="text-sm font-medium">Filename match (optional glob)</span>
          <input
            className={inputCls}
            placeholder="sales_*.txt"
            value={glob}
            onChange={(e) => setGlob(e.target.value)}
          />
        </label>

        {error ? <ErrorBanner message={error} /> : null}
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={create} disabled={saving || !name.trim()}>
            {saving ? "Creating…" : "Create template"}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}

function PreviewDialog({
  template,
  onClose,
}: {
  template: FeedTemplate | null;
  onClose: () => void;
}) {
  const [preview, setPreview] = useState<FeedTemplatePreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function onPick(file: File) {
    if (!template) return;
    setLoading(true);
    setError(null);
    setPreview(null);
    try {
      setPreview(await api.previewFeedTemplate(template.id, file));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not parse the sample.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog
      open={template !== null}
      onClose={() => {
        setPreview(null);
        setError(null);
        onClose();
      }}
      title={`Test — ${template?.name ?? ""}`}
      description="Upload a sample file to see how this template parses it."
    >
      <div className="space-y-4">
        <input
          ref={fileRef}
          type="file"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void onPick(f);
          }}
        />
        <Button variant="outline" onClick={() => fileRef.current?.click()}>
          <Upload className="h-4 w-4" /> Choose sample file
        </Button>
        {loading ? <p className="text-sm text-muted-foreground">Parsing…</p> : null}
        {error ? <ErrorBanner message={error} /> : null}
        {preview ? (
          <div className="space-y-2">
            {preview.signature_matches !== null ? (
              <Badge variant={preview.signature_matches ? "success" : "warning"}>
                {preview.signature_matches
                  ? "Matches expected columns"
                  : "Columns differ from expected"}
              </Badge>
            ) : null}
            <div className="overflow-x-auto rounded-md border border-border">
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    {preview.columns.map((c, i) => (
                      <th key={i} className="px-2 py-1 text-left font-medium">
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.rows.slice(0, 10).map((row, ri) => (
                    <tr key={ri} className="border-t border-border hover:bg-muted/40">
                      {row.map((cell, ci) => (
                        <td key={ci} className="px-2 py-1 tabular-nums">
                          {cell ?? ""}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-muted-foreground">{preview.row_count} data row(s) parsed.</p>
          </div>
        ) : null}
      </div>
    </Dialog>
  );
}

"use client";

import { ArrowRight, CheckCircle2, FileSpreadsheet, Layers, UploadCloud } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { ErrorBanner } from "@/components/ui/feedback";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api/client";
import type { FileRead, SheetAutoMap, SheetRead } from "@/lib/api/types";

type Step = "pick" | "processing" | "done";

/**
 * Guided "add a source" flow: pick a file → detect structure → review detected
 * sheets → jump into mapping. Sequences the existing upload + process endpoints so
 * first-time users aren't left clicking around four disconnected screens.
 */
export function AddSourceWizard({
  open,
  onClose,
  onCompleted,
}: {
  open: boolean;
  onClose: () => void;
  onCompleted: () => void;
}) {
  const router = useRouter();
  const toast = useToast();
  const [step, setStep] = useState<Step>("pick");
  const [mode, setMode] = useState<"upload" | "path">("upload");
  const [picked, setPicked] = useState<File | null>(null);
  const [pathInput, setPathInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{
    file: FileRead;
    sheets: SheetRead[];
    matchedTemplate: string | null;
    autoMap: SheetAutoMap[];
  } | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const reset = useCallback(() => {
    setStep("pick");
    setMode("upload");
    setPicked(null);
    setPathInput("");
    setError(null);
    setResult(null);
    if (fileInput.current) fileInput.current.value = "";
  }, []);

  const close = useCallback(() => {
    reset();
    onClose();
  }, [reset, onClose]);

  const canDetect = mode === "upload" ? picked !== null : pathInput.trim().length > 0;

  async function onDetect() {
    if (!canDetect) return;
    setStep("processing");
    setError(null);
    try {
      const { file } =
        mode === "upload" ? await api.uploadFile(picked!) : await api.ingestByPath(pathInput.trim());
      const processed = await api.processFile(file.id);
      setResult({
        file,
        sheets: processed.sheets,
        matchedTemplate: processed.matched_template,
        autoMap: processed.auto_map,
      });
      setStep("done");
      onCompleted();
      toast.success(`Detected ${processed.sheets.length} sheet(s) in ${file.filename}.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not process the file.");
      setStep("pick");
      toast.error("Source ingestion failed.");
    }
  }

  function openFile(fileId: string) {
    close();
    router.push(`/files/${fileId}`);
  }

  function openMapping(sheetId: string) {
    close();
    router.push(`/sheets/${sheetId}/mapping`);
  }

  return (
    <Dialog
      open={open}
      onClose={close}
      title="Add a data source"
      description="Upload a marketing data file. We'll detect its structure and guide you to mapping."
    >
      {step === "pick" ? (
        <div className="space-y-4">
          <div className="inline-flex rounded-md border border-border p-0.5 text-sm">
            {(["upload", "path"] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => {
                  setMode(m);
                  setError(null);
                }}
                className={
                  mode === m
                    ? "rounded px-3 py-1 bg-primary text-primary-foreground"
                    : "rounded px-3 py-1 text-muted-foreground hover:text-foreground"
                }
              >
                {m === "upload" ? "Upload" : "By path (large files)"}
              </button>
            ))}
          </div>

          {mode === "upload" ? (
            <button
              type="button"
              onClick={() => fileInput.current?.click()}
              className="flex w-full flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border py-10 text-center transition-colors hover:border-primary/50 hover:bg-accent"
            >
              <UploadCloud className="h-7 w-7 text-muted-foreground" />
              {picked ? (
                <span className="text-sm font-medium text-foreground">{picked.name}</span>
              ) : (
                <>
                  <span className="text-sm font-medium text-foreground">
                    Click to choose a CSV or XLSX
                  </span>
                  <span className="text-xs text-muted-foreground">
                    Multi-tab workbooks are detected sheet by sheet.
                  </span>
                </>
              )}
            </button>
          ) : (
            <div className="space-y-1.5">
              <input
                className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                placeholder="/data/landing/spend_2026.csv"
                value={pathInput}
                onChange={(e) => {
                  setPathInput(e.target.value);
                  setError(null);
                }}
              />
              <p className="text-xs text-muted-foreground">
                A server-side path within an allowlisted landing zone. The backend reads it by
                reference — nothing is uploaded through the browser (best for very large files).
              </p>
            </div>
          )}
          <input
            ref={fileInput}
            type="file"
            accept=".csv,.tsv,.psv,.txt,.dat,.xlsx"
            className="hidden"
            onChange={(e) => {
              setPicked(e.target.files?.[0] ?? null);
              setError(null);
            }}
          />
          {error ? <ErrorBanner message={error} /> : null}
          <ol className="space-y-1 text-xs text-muted-foreground">
            <li>1 · Detect structure & profile columns</li>
            <li>2 · Map columns to the canonical schema (AI can suggest)</li>
            <li>3 · Transform, validate, and generate clean output</li>
          </ol>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={close}>
              Cancel
            </Button>
            <Button onClick={onDetect} disabled={!canDetect}>
              Detect structure <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      ) : null}

      {step === "processing" ? (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Layers className="h-4 w-4 animate-pulse" /> Detecting structure & profiling columns…
          </div>
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-4 w-2/3" />
        </div>
      ) : null}

      {step === "done" && result ? (
        <div className="space-y-4">
          <div className="flex items-center gap-2 rounded-md border border-success/30 bg-success/10 px-3 py-2 text-sm text-success">
            <CheckCircle2 className="h-4 w-4" />
            <span>
              {result.file.filename} — {result.sheets.length} sheet
              {result.sheets.length === 1 ? "" : "s"} detected.
            </span>
          </div>
          {result.matchedTemplate ? (
            <div className="rounded-md border border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
              Parsed with feed template <span className="font-medium text-foreground">{result.matchedTemplate}</span>.
            </div>
          ) : null}
          <div className="space-y-2">
            {result.sheets.map((s) => {
              const am = result.autoMap.find((a) => a.sheet_id === s.id);
              return (
                <div
                  key={s.id}
                  className="flex items-center gap-3 rounded-lg border border-border p-3"
                >
                  <FileSpreadsheet className="h-4 w-4 text-muted-foreground" />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">{s.sheet_name}</div>
                    <div className="text-xs text-muted-foreground tabular-nums">
                      {s.columns.length} column{s.columns.length === 1 ? "" : "s"}
                      {am?.auto_mapped
                        ? am.is_complete
                          ? " · auto-mapped ✓"
                          : ` · auto-mapped, ${am.missing_required.length} required missing`
                        : ""}
                    </div>
                  </div>
                  <Button
                    variant={am?.auto_mapped ? "ghost" : "outline"}
                    size="sm"
                    onClick={() => openMapping(s.id)}
                  >
                    {am?.auto_mapped ? "Review mapping" : "Map columns"}{" "}
                    <ArrowRight className="h-3.5 w-3.5" />
                  </Button>
                </div>
              );
            })}
          </div>
          <div className="flex justify-between gap-2">
            <Button variant="ghost" onClick={reset}>
              Add another
            </Button>
            <Button onClick={() => openFile(result.file.id)}>
              Open file <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      ) : null}
    </Dialog>
  );
}

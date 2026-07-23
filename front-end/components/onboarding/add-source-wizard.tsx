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
import type { FileRead, SheetRead } from "@/lib/api/types";

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
  const [picked, setPicked] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ file: FileRead; sheets: SheetRead[] } | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const reset = useCallback(() => {
    setStep("pick");
    setPicked(null);
    setError(null);
    setResult(null);
    if (fileInput.current) fileInput.current.value = "";
  }, []);

  const close = useCallback(() => {
    reset();
    onClose();
  }, [reset, onClose]);

  async function onDetect() {
    if (!picked) return;
    setStep("processing");
    setError(null);
    try {
      const { file } = await api.uploadFile(picked);
      const processed = await api.processFile(file.id);
      setResult({ file, sheets: processed.sheets });
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
          <input
            ref={fileInput}
            type="file"
            accept=".csv,.xlsx"
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
            <Button onClick={onDetect} disabled={!picked}>
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
          <div className="space-y-2">
            {result.sheets.map((s) => (
              <div
                key={s.id}
                className="flex items-center gap-3 rounded-lg border border-border p-3"
              >
                <FileSpreadsheet className="h-4 w-4 text-muted-foreground" />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium">{s.sheet_name}</div>
                  <div className="text-xs text-muted-foreground tabular-nums">
                    {s.columns.length} column{s.columns.length === 1 ? "" : "s"}
                  </div>
                </div>
                <Button variant="outline" size="sm" onClick={() => openMapping(s.id)}>
                  Map columns <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))}
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

"use client";

// Assemble-stack wizard (Cycle 5, Phase 16): pick cleaned (Silver) outputs →
// harmonize across sources (AI-assisted) → create a draft Stack (Gold).

import { Sparkles } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { AiSuggestionList, type AiSuggestionItem } from "@/components/ai/suggestion-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api/client";
import type { JobListItem } from "@/lib/api/types";

const inputCls =
  "h-9 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

type Step = "pick" | "harmonize";

export function AssembleStackWizard({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (stackId: string) => void;
}) {
  const { success, error, info } = useToast();
  const [step, setStep] = useState<Step>("pick");
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [name, setName] = useState("");
  const [grain, setGrain] = useState("weekly");
  // Accepted channel harmonizations: raw value -> canonical value.
  const [valueMap, setValueMap] = useState<Record<string, string>>({});
  const [suggestions, setSuggestions] = useState<AiSuggestionItem[]>([]);
  const [busy, setBusy] = useState(false);

  const reset = useCallback(() => {
    setStep("pick");
    setSelected(new Set());
    setName("");
    setGrain("weekly");
    setValueMap({});
    setSuggestions([]);
  }, []);

  useEffect(() => {
    if (!open) return;
    reset();
    api
      .listJobs()
      .then((all) => setJobs(all.filter((j) => j.job.status === "succeeded")))
      .catch(() => setJobs([]));
  }, [open, reset]);

  function toggle(jobId: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(jobId)) next.delete(jobId);
      else next.add(jobId);
      return next;
    });
  }

  async function suggest() {
    setBusy(true);
    try {
      const res = await api.harmonizationSuggestions([...selected], "channel");
      const items: AiSuggestionItem[] = res.suggestions
        .filter((s) => !(s.raw in valueMap))
        .map((s) => ({ id: s.raw, title: `${s.raw} → ${s.canonical}`, subtitle: "channel" }));
      setSuggestions(items);
      if (items.length === 0) info("No new channel harmonizations suggested.");
    } catch (e) {
      if (e instanceof ApiError && e.isLlmDisabled) info("AI is disabled — harmonize manually.");
      else error(e instanceof Error ? e.message : "Could not fetch suggestions.");
    } finally {
      setBusy(false);
    }
  }

  function acceptSuggestion(item: AiSuggestionItem) {
    const [raw, canonical] = item.title.split(" → ");
    setValueMap((prev) => ({ ...prev, [raw]: canonical }));
    setSuggestions((prev) => prev.filter((s) => s.id !== item.id));
  }

  function dismissSuggestion(item: AiSuggestionItem) {
    setSuggestions((prev) => prev.filter((s) => s.id !== item.id));
  }

  async function create() {
    setBusy(true);
    try {
      const stack = await api.createStack({
        name: name.trim() || "New stack",
        source_job_ids: [...selected],
        grain,
        harmonization: Object.keys(valueMap).length ? { value_map: { channel: valueMap } } : undefined,
      });
      success("Stack assembled as a draft.");
      onCreated(stack.id);
    } catch (e) {
      error(e instanceof Error ? e.message : "Could not assemble the stack.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Assemble a stack"
      description="Combine cleaned per-source outputs into one model-ready panel (Gold)."
      className="max-w-2xl"
    >
      <ol className="mb-4 flex gap-2 text-xs">
        {(["pick", "harmonize"] as const).map((s, i) => (
          <li
            key={s}
            className={
              step === s
                ? "rounded bg-primary px-2 py-1 text-primary-foreground"
                : "rounded bg-muted px-2 py-1 text-muted-foreground"
            }
          >
            {i + 1}. {s === "pick" ? "Pick sources" : "Harmonize"}
          </li>
        ))}
      </ol>

      {step === "pick" && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Stack name</label>
              <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} placeholder="Q1 media panel" />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Grain</label>
              <select className={inputCls} value={grain} onChange={(e) => setGrain(e.target.value)}>
                <option value="daily">daily</option>
                <option value="weekly">weekly</option>
                <option value="monthly">monthly</option>
              </select>
            </div>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">
              Source outputs (Silver) — {selected.size} selected
            </label>
            <div className="max-h-56 space-y-1 overflow-y-auto rounded-md border border-border p-2">
              {jobs.length === 0 ? (
                <p className="px-1 py-2 text-xs text-muted-foreground">
                  No succeeded jobs with output yet. Run a pipeline first.
                </p>
              ) : (
                jobs.map((j) => (
                  <label key={j.job.id} className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-accent">
                    <input type="checkbox" checked={selected.has(j.job.id)} onChange={() => toggle(j.job.id)} />
                    <span className="flex-1 truncate">{j.filename ?? "file"}</span>
                    <Badge variant="success">{j.job.status}</Badge>
                  </label>
                ))
              )}
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" size="sm" onClick={onClose}>Cancel</Button>
            <Button size="sm" onClick={() => setStep("harmonize")} disabled={selected.size === 0}>
              Next
            </Button>
          </div>
        </div>
      )}

      {step === "harmonize" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Unify channel names across sources. AI suggests; you approve (CC-5).
            </p>
            <Button variant="outline" size="sm" onClick={suggest} disabled={busy}>
              <Sparkles className="h-4 w-4" /> Suggest harmonization
            </Button>
          </div>

          <AiSuggestionList
            title="Channel harmonization"
            items={suggestions}
            onAccept={acceptSuggestion}
            onDismiss={dismissSuggestion}
            emptyHint="Click “Suggest harmonization” to detect channel aliases across your sources."
          />

          {Object.keys(valueMap).length > 0 && (
            <div className="space-y-1.5">
              <div className="text-xs font-medium text-muted-foreground">Accepted mappings</div>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(valueMap).map(([raw, canonical]) => (
                  <Badge key={raw} variant="secondary">{raw} → {canonical}</Badge>
                ))}
              </div>
            </div>
          )}

          <div className="flex justify-between gap-2">
            <Button variant="ghost" size="sm" onClick={() => setStep("pick")}>Back</Button>
            <Button size="sm" onClick={create} disabled={busy}>
              {busy ? "Assembling…" : "Assemble stack"}
            </Button>
          </div>
        </div>
      )}
    </Dialog>
  );
}

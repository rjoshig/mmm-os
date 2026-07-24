"use client";

// Shared AI-suggestion list (Cycle 5) — the Sparkles accept/dismiss pattern,
// factored out of the mapping/transform pages for reuse (e.g. harmonization).
// AI suggests; the human accepts or dismisses (CC-5).

import { Check, Sparkles, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export interface AiSuggestionItem {
  id: string;
  title: string;
  subtitle?: string;
  /** 0–1 confidence, rendered as a percentage badge when present. */
  confidence?: number | null;
}

export function AiSuggestionList({
  title,
  items,
  onAccept,
  onDismiss,
  emptyHint,
}: {
  title: string;
  items: AiSuggestionItem[];
  onAccept: (item: AiSuggestionItem) => void;
  onDismiss: (item: AiSuggestionItem) => void;
  emptyHint?: string;
}) {
  return (
    <div className="rounded-lg border border-primary/30 bg-primary/5 p-4">
      <div className="mb-3 flex items-center gap-2 text-sm font-medium">
        <Sparkles className="h-4 w-4 text-primary" />
        {title}
      </div>
      {items.length === 0 ? (
        <p className="text-xs text-muted-foreground">{emptyHint ?? "No suggestions."}</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item) => (
            <li
              key={item.id}
              className="flex items-center justify-between gap-3 rounded-md border border-border bg-card px-3 py-2"
            >
              <div className="min-w-0">
                <div className="truncate text-sm font-medium">{item.title}</div>
                {item.subtitle && (
                  <div className="truncate text-xs text-muted-foreground">{item.subtitle}</div>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-1.5">
                {item.confidence != null && (
                  <Badge variant="outline">{Math.round(item.confidence * 100)}%</Badge>
                )}
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onAccept(item)}
                  aria-label="Accept suggestion"
                >
                  <Check className="h-4 w-4" />
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => onDismiss(item)}
                  aria-label="Dismiss suggestion"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

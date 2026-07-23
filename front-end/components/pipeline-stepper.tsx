"use client";

import { Check, FileSearch, ShieldCheck, Table2, Wand2 } from "lucide-react";
import Link from "next/link";
import { Tooltip } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import type { FilePipelineStatus, SheetPipelineStatus } from "@/lib/api/types";

/**
 * Per-sheet pipeline stepper for the file-detail page.
 *
 * Renders Ingested → Mapped → Transformed → Validated → Ready, lighting up the
 * furthest reached stage and linking the NEXT incomplete step so the user always
 * knows what to do. Validation/output are file-(job-)level today.
 */
const STAGES = ["Ingested", "Mapped", "Transformed", "Validated", "Ready"] as const;

function stageState(
  sheet: SheetPipelineStatus,
  file: FilePipelineStatus
): { reached: number; nextHref?: string } {
  // Ingested(0) always done for an existing sheet.
  let reached = 0;
  let nextHref: string | undefined = `/sheets/${sheet.sheet_id}/mapping`;
  if (!sheet.has_mapping) return { reached, nextHref };
  reached = 1;
  nextHref = `/sheets/${sheet.sheet_id}/transform`;
  if (!sheet.has_rule_set) return { reached, nextHref };
  reached = 2;
  nextHref = undefined; // validate/generate are file-level actions on the page
  if (!file.validated) return { reached, nextHref };
  reached = 3;
  if (file.blocking_open > 0 || !file.has_output) return { reached, nextHref };
  reached = 4;
  return { reached, nextHref: undefined };
}

const STAGE_ICON = [FileSearch, Table2, Wand2, ShieldCheck, Check];
const STAGE_HINT = [
  "File ingested and profiled",
  "Map source columns to the canonical schema",
  "Apply transform rules (clean, standardize, aggregate)",
  "Run validation to check data quality",
  "Generate clean, model-ready output",
];

export function PipelineStepper({
  sheet,
  file,
}: {
  sheet: SheetPipelineStatus;
  file: FilePipelineStatus;
}) {
  const { reached, nextHref } = stageState(sheet, file);

  return (
    <div className="flex flex-wrap items-center gap-1">
      {STAGES.map((label, i) => {
        const Icon = STAGE_ICON[i];
        const done = i <= reached;
        const isNext = i === reached + 1 && nextHref !== undefined;
        const hint = done
          ? `${label} — done`
          : isNext
            ? `Next: ${STAGE_HINT[i]}`
            : STAGE_HINT[i];
        const content = (
          <Tooltip content={hint}>
            <span
              className={cn(
                "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-medium",
                done
                  ? "bg-success/15 text-success"
                  : isNext
                    ? "bg-primary/10 text-primary ring-1 ring-primary/30"
                    : "bg-muted text-muted-foreground"
              )}
            >
              <Icon className="h-3 w-3" />
              {label}
            </span>
          </Tooltip>
        );
        return (
          <span key={label} className="flex items-center gap-1">
            {nextHref && isNext ? (
              <Link href={nextHref} className="hover:opacity-80">
                {content}
              </Link>
            ) : (
              content
            )}
            {i < STAGES.length - 1 ? (
              <span className="text-muted-foreground/40">›</span>
            ) : null}
          </span>
        );
      })}
    </div>
  );
}

import { cn } from "@/lib/utils";

/** A shimmering placeholder block for loading states. */
export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-md bg-muted", className)} />;
}

/** A skeleton stand-in for a data table while it loads. */
export function TableSkeleton({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <div className="flex gap-4 border-b border-border bg-muted/40 px-4 py-2.5">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-3.5 flex-1" />
        ))}
      </div>
      <div className="divide-y divide-border">
        {Array.from({ length: rows }).map((_, r) => (
          <div key={r} className="flex gap-4 px-4 py-3">
            {Array.from({ length: cols }).map((_, c) => (
              <Skeleton key={c} className={cn("h-4 flex-1", c === 0 && "max-w-[40%]")} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

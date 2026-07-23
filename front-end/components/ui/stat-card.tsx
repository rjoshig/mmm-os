import { Info } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Tooltip } from "@/components/ui/tooltip";

/** A compact metric tile for dashboards; ``hint`` shows as an info tooltip. */
export function StatCard({
  label,
  value,
  icon,
  hint,
}: {
  label: string;
  value: string | number;
  icon?: React.ReactNode;
  hint?: string;
}) {
  return (
    <Card className="p-4">
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-1 text-xs font-medium text-muted-foreground">
          {label}
          {hint ? (
            <Tooltip content={hint}>
              <Info className="h-3 w-3 cursor-help text-muted-foreground/70" />
            </Tooltip>
          ) : null}
        </span>
        {icon}
      </div>
      <div className="mt-2 text-2xl font-semibold tabular-nums tracking-tight">{value}</div>
    </Card>
  );
}

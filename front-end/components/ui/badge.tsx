import { cn } from "@/lib/utils";

type Variant = "default" | "secondary" | "success" | "warning" | "destructive" | "outline";

const VARIANTS: Record<Variant, string> = {
  default: "border-transparent bg-primary/10 text-primary",
  secondary: "border-transparent bg-secondary text-secondary-foreground",
  success: "border-transparent bg-success/12 text-success",
  warning: "border-transparent bg-tertiary/20 text-foreground",
  destructive: "border-transparent bg-destructive/12 text-destructive",
  outline: "border-border text-muted-foreground",
};

/** A small status pill. Colors come from semantic tokens only. */
export function Badge({
  variant = "default",
  className,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { variant?: Variant }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-medium",
        VARIANTS[variant],
        className
      )}
      {...props}
    />
  );
}

/** Map a backend status/severity string to a Badge variant. */
export function statusVariant(status: string | null | undefined): Variant {
  switch ((status || "").toLowerCase()) {
    case "succeeded":
    case "parsed":
    case "resolved":
    case "accepted":
      return "success";
    case "failed":
    case "block":
    case "error":
      return "destructive";
    case "needs_review":
    case "running":
    case "pending":
    case "warn":
    case "warning":
      return "warning";
    default:
      return "secondary";
  }
}

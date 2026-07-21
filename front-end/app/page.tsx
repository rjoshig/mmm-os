import { Database, GitBranch, ShieldCheck, Sparkles } from "lucide-react";

/**
 * Placeholder landing page for the mmm-os UI shell.
 *
 * This is scaffolding only — no feature screens. The Review UI (job dashboard,
 * mapping review, transformation builder, validation review) is built in Phase 6
 * (see docs/phases/phase-06-review-ui-nextjs.md). Its purpose here is to prove
 * the theme, fonts, and layout render correctly.
 */
export default function Home() {
  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <span className="text-xs font-medium uppercase tracking-wide text-primary">
          Repository initialized
        </span>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">mmm-os</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">
          Marketing Data Ingestion &amp; Transformation Platform. This is the UI shell — feature
          screens arrive in Phase 6. The pipeline ingests messy CSV/XLSX files, maps columns to a
          canonical schema, transforms them via a config-driven rule engine, and validates the
          output, with an AI suggest-not-decide layer and a human review loop.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <FeatureCard
          icon={<Database className="h-4 w-4 text-primary" />}
          title="Ingest & profile"
          body="Land files immutably; parse multi-tab workbooks; detect structure."
        />
        <FeatureCard
          icon={<GitBranch className="h-4 w-4 text-primary" />}
          title="Map & transform"
          body="Reusable saved configs; a declarative, layered rule engine."
        />
        <FeatureCard
          icon={<ShieldCheck className="h-4 w-4 text-success" />}
          title="Validate"
          body="Quality checks & anomaly detection flag issues for review."
        />
        <FeatureCard
          icon={<Sparkles className="h-4 w-4 text-primary" />}
          title="AI suggestions"
          body="Draft mappings & labels with confidence — humans ratify."
        />
      </div>

      <p className="text-xs text-muted-foreground">
        See <code className="mono rounded bg-muted px-1 py-0.5">docs/</code> for the PRD, build
        plan, and phase specs.
      </p>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  body,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-4 text-card-foreground shadow-sm">
      <div className="flex items-center gap-2">
        {icon}
        <h2 className="text-sm font-semibold">{title}</h2>
      </div>
      <p className="mt-2 text-xs text-muted-foreground">{body}</p>
    </div>
  );
}

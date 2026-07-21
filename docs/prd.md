# Product Requirements Document
## Marketing Data Ingestion & Transformation Platform (Mutinex DataOS–inspired)

**Status:** Draft v0.1 — working reference
**Source of truth:** derived from the project PRD. Companion: [`build-plan.md`](./build-plan.md).

---

## 1. Background & Context

Marketing Mix Modelling (MMM) and marketing analytics depend on **clean, unified,
standardised data**. In practice, getting that data ready is the hardest and most
manual part of the whole process — data arrives fragmented across dozens of
platforms, teams, and file formats, and must be reshaped into a consistent
structure before any model or analysis can use it.

Mutinex **DataOS** is the reference product for this space. It is a *data
provisioning layer* that sits **upstream** of modelling. Its stated value: turn
messy marketing data into clean, harmonised, validated inputs — with no
data-warehouse maintenance required, and usable by marketers rather than data
scientists. Customers have reported cutting data-warehouse build time by ~70%,
and its AI auto-labelling feature ("Data MAITE") claims up to 95% reduction in
labelling time.

**What DataOS actually does (the three core jobs):**
1. **Mapping** — map raw customer columns to a standard schema.
2. **Transformation** — standardise, clean, dedupe, harmonise taxonomies.
3. **Validation** — automated quality/anomaly checks with human review.

It is essentially a **marketing-specific ETL tool with a friendly UI and an
AI-assisted mapping layer**. It is deliberately *opinionated* (bounded to the MMM
domain), which is what makes it usable by non-technical people.

> **Scope note:** DataOS is NOT the modelling engine. This project is likewise
> **only the data ingestion + transformation layer**. No modelling.

---

## 2. What We Are Building

A **multi-tenant, scalable platform** that automatically ingests marketing data
files (primarily **CSV / XLSX, including multi-tab workbooks**), cleans and
transforms them via a **config-driven rule engine**, and outputs clean,
structured, model-ready tabular data — with **AI-assisted mapping/labelling** and
a **human approve-reject review loop**.

**Primary goal:** configure once per customer + file-type, then run automatically
on every refresh.

### 2.1 In scope
- Automated ingestion of CSV / XLSX (multi-tab) files
- Auto-detection of file structure (header rows, data sheets, types)
- Column mapping to a standard schema, with **reusable saved configs**
- Config-driven transformations (declarative rule engine)
- Taxonomy harmonisation (standard vocabulary for channels/markets/products)
- Automated validation / anomaly detection with review flags
- AI suggestions for mapping, labelling, and structure detection (suggest-not-decide)
- Scheduled / repeatable refreshes reusing saved config
- Multi-tenant isolation and governance

### 2.2 Out of scope (for now)
- The modelling / MMM engine itself
- PDF and email ingestion (unstructured — treated as **future extra scope**, see §4.4)
- API connectors to ad platforms (deferred — file ingestion first; see §4.1)

### 2.3 Explicitly deferred / to decide
- Depth of API-connector support (Meta, Google, TikTok, etc.)
- PDF/email extraction layer
- How far the "escape hatch" custom-rule capability should go

---

## 3. Data Sources

| Source type | Priority | Notes |
|---|---|---|
| **CSV files** | P0 | Single datasheet per file. |
| **XLSX / XLS (multi-tab)** | P0 | Each sheet treated as its own table; detect & skip empty sheets. |
| **API connectors** (Meta, Google, TikTok, CRM, e-commerce, ERP) | P2 (deferred) | DataOS connects to 200+ sources out of the box; this is the hardest, least glamorous part and changes often. Budget heavily if/when included. |
| **PDF** | Future | Unstructured — needs OCR/LLM extraction step *before* the normal pipeline. Not confirmed as a DataOS capability. |
| **Email (+ attachments)** | Future | Unstructured — parsing + attachment handling. Not confirmed as a DataOS capability. |

**Key point:** DataOS is built around **tabular** data. PDF/email are a separate,
harder problem requiring an extraction step that turns them *into* tables first.
Do not assume they are "standard."

---

## 4. Core Capabilities (what DataOS does that we will build)

1. **Multi-source ingestion** — file uploads (CSV/XLS, multi-tab); API connectors later.
2. **Auto-structure detection** — header-row detection, type inference, multi-sheet handling, skipping junk/title rows and merged cells.
3. **Column mapping** — match messy columns → standard schema; **reusable, saved-per-customer** mapping configs.
4. **AI-assisted labelling** — suggest mappings & taxonomy labels; human approves.
5. **Taxonomy harmonisation** — one standard vocabulary across channels / markets / products.
6. **Transformations** — standardisation, dedup, reshaping (wide→long), currency/date/unit normalisation.
7. **Validation / anomaly detection** — automated quality checks with review flags.
8. **Scheduled refreshes** — re-run pipelines without redoing config.
9. **Clean structured output** — model-ready tabular data.
10. **Governance** — roles, access control, audit logs, tenant isolation.

### 4.1 MVP core (nail these three first)
1. **Ingest + auto-detect structure** (multi-tab, messy headers) — the foundation.
2. **Mapping engine with saved configs** — the reusable brain; this is the actual product.
3. **Transformation + validation** — what makes output trustworthy.

Everything else (AI suggestions, connectors, scheduling, multi-tenant scale)
layers on top of these three. API connectors can be skipped entirely at first —
file ingestion alone is most of DataOS's value.

### 4.4 Extraction layer (PDF/email — future)
The messiest, most failure-prone piece if added. Requires OCR/LLM to convert
unstructured input → tables, plus a human-review fallback. Keep out of MVP.

---

## 5. The Ingestion & ETL Flow

For an automatically-arriving multi-tab Excel file:

1. **Ingest / Land** — file lands (upload, watched folder, email drop, or API). Store an immutable raw copy in object storage; create a job record with status tracking.
2. **Split tabs** — each sheet in an .xlsx becomes its own candidate table; detect which sheets contain data, skip empties.
3. **Detect structure (per sheet)** — find the real header row (skip title rows, merged cells, notes); infer column types and date formats.
4. **Map columns** — match columns → standard schema (date, channel, campaign, spend, impressions, revenue, …). AI suggests; user confirms on first run; mapping saved per customer + file-type.
5. **Transform / standardise** — normalise values (taxonomy alignment), fix units/currency/dates, dedupe, reshape wide→long if needed.
6. **Validate** — check gaps, negatives, outliers, missing dates, duplicates → flag for human review.
7. **Load / Output** — write clean, structured rows to the warehouse, tagged by customer.
8. **Refresh** — same file type next period reuses saved mapping → runs automatically.

**The magic is steps 4→8: configure once, auto-run forever after.** First
onboarding is manual; every refresh after is near-automatic.

---

## 6. The Transformation / Rule Engine

**Design principle:** flexibility (config, not hardcode) **and** intuitive
creation. These pull against each other; the resolution is a declarative engine
underneath + an action-based UI on top.

### 6.1 Declarative rule schema
Store each customer's transformations as **data** (JSON/YAML rows in the database),
not code.

A rule is roughly:
```
{ target_field, operation, params, condition }
```
Operation library (extensible): `map_value`, `rename_column`, `cast_type`, `parse_date`,
`convert_currency`, `dedupe`, `reshape`, `fill_missing`, … plus a raw/custom escape-hatch type.

The engine reads config and applies rules in order. **Adding a capability =
adding an operation type**, not rewriting per customer.

### 6.2 Layered rules (keeps config manageable)
- **Global defaults** — apply to everyone (e.g. standard date parsing).
- **Template rules** — per file-type / per source (e.g. "Meta export").
- **Customer overrides** — tenant-specific tweaks.

Merge at runtime. Stops every customer becoming a from-scratch snowflake.

### 6.3 Intuitive creation (don't make users write config)
Users act on a **data preview**; their actions generate config behind the scenes.
Click a column → pick "map values" → see distinct values → assign standards. Each
action writes a rule to the schema. Users never see JSON. (Pattern: Trifacta /
Power Query.)

### 6.4 Preview-driven
Every rule shows **before/after on real sample rows** immediately. This is what
makes it feel intuitive and trustworthy rather than abstract.

**Summary:** declarative engine (flexible) + action-based UI that authors config
(intuitive) + live preview (trustworthy).

### 6.5 Flexibility stance — decision
Lean toward an **opinionated engine with an escape hatch**: a fixed library of
well-designed operations covering ~90% of cases, plus a raw/custom rule type for
the rest. Keeps the UI intuitive and AI suggestions sharp, without boxing us in.
(Fully general engine = powerful but intimidating; fully fixed = too rigid.)

> **Open decision:** how far the escape-hatch custom rule goes. See
> [`open-questions.md`](./open-questions.md) OQ-3.1.

---

## 7. AI Layer (mirrors "Data MAITE")

**Guiding rule: suggest, don't decide.** AI accelerates the work but never
bypasses human oversight — users **accept, reject, or modify** every machine
suggestion. AI writes *draft config*; humans ratify it into saved rules.

### 7.1 Where AI helps
- **Column mapping suggestions** — given headers + sample values, propose which standard field each maps to, **with a confidence score**. High confidence auto-fills; low confidence flags for review.
- **Value / taxonomy suggestions** — given distinct raw values ("FB", "fb_ads", "Facebook"), propose the canonical label to collapse them into.
- **Structure detection** — where's the header row, which sheets are data, which is the date column.
- **Anomaly explanations** — not just "outlier flagged" but "spend jumped 400% on this date, likely a duplicate."

### 7.2 Where it plugs into the flow
AI runs **between profiling (§5 step 3) and user confirmation (step 4)**. It
pre-populates config as suggestions; the human approve/reject step turns
suggestions into saved rules. AI is an accelerant *on top of the same rule
engine* — it never bypasses the rule store.

### 7.3 AI design principles
- Feed the AI **distinct values + column stats**, not raw data dumps — cheaper, more accurate, avoids sending full customer data to the model.
- **Store the reasoning** behind each suggestion so the review UI can show *why*.
- Confidence-thresholded behaviour (auto-fill vs flag).
- Bounded/opinionated domain makes suggestions much sharper.

---

## 8. Multi-Tenancy & Scalability (the major engineering work)

In rough priority:

1. **Tenant isolation** — every row, file, and config scoped to a customer; no leakage. Decide row-level (`tenant_id` everywhere) vs schema/DB-per-tenant. **Hard to reverse — decide early.**
2. **Async processing** — 60 files can't run in a web request. Job queue (Celery/RQ or managed) + workers; background processing with per-file status and retries.
3. **Per-tenant config store** — mappings, taxonomies, validation rules, versioned. This *is* the product's memory.
4. **Extraction layer** (only if PDF/email included) — heaviest, most failure-prone; needs human-review fallback.
5. **Schema flexibility** — per-tenant custom fields / business hierarchies on top of the standard schema.
6. **Observability + review UI** — dashboards for what failed, what needs approval, and why. We'll live in this screen.
7. **Scale mechanics** — stream/chunk large files (don't load 100MB into memory), autoscale workers, per-tenant rate limiting so one customer's dump doesn't starve others.
8. **Security / compliance** — encryption, access roles, audit logs (DataOS leans on SOC 2-compliant infra with admin-controlled roles). Enterprise buyers will require similar.

---

## 9. Proposed Tech Stack

| Layer | Choice | Rationale |
|---|---|---|
| Frontend | **Next.js (React)** | Rich, interactive mapping tables + approve/reject flows. |
| Backend API | **Python (FastAPI)** | Ideal for data work (pandas/polars), easy LLM integration. |
| Workers | **Celery / RQ** | Async batch file processing. |
| Metadata + configs | **Postgres** (SQLite in dev) | Tenants, files, mappings, jobs, rules. |
| Raw files | **Object storage (S3/GCS)** | Immutable raw copies. |
| Clean data | **Warehouse** | Model-ready structured output. |
| AI | **LLM** | Mapping/labelling/structure suggestions. |

**Note on UI choice:** Python web UIs (Streamlit/Dash) are fine for prototypes but
painful for a real product; Next.js + FastAPI API is the scalable path. Backend
Python is strongly the right call.

> **Implementation note for this repo:** the metadata/config database is SQLite in
> development and swappable to Postgres via an env-var URL only. The UI (Prisma)
> database is separate and follows the same swap approach. See
> [`architecture.md`](./architecture.md).

---

## 10. Reality Checks / Risks

- **File cleaning is ~70% of the work and never fully "solves"** — real customer files are endlessly inconsistent. The mapping/config engine + human-review loop is where most time goes, not the UI.
- **API connectors** (if added) are the hardest, least glamorous part; every platform API differs and changes often.
- **PDF/email extraction** is unreliable — keep out of MVP; expect human fallback if added.
- **Tenant isolation model** is hard to change later — decide up front.
- The AI must remain **suggest-not-decide** to stay trustworthy.

---

## 11. Open Decisions

Tracked in [`open-questions.md`](./open-questions.md). In summary:

1. Tenant isolation model: row-level vs schema/DB-per-tenant.
2. How flexible the escape-hatch custom rule should be.
3. Whether/when to add API connectors.
4. Whether/when to add PDF/email extraction.
5. Standard schema definition (the canonical target fields).
6. Transformation library — exact operation set for v1.

---

## 12. Next Steps

These are elaborated as the phased [`build-plan.md`](./build-plan.md):

1. **Define the standard/canonical schema** — the target fields everything maps to.
2. **Data model** — tenants, files, mappings, rules, jobs (tables + relationships).
3. **Rule schema in detail** — concrete stored-rule shape + v1 operation library.
4. **AI suggestion loop** — profiling → suggestion → confidence → review → saved rule.
5. **Ingestion pipeline** — structure detection for multi-tab/messy files.
6. **Multi-tenant + async architecture** — queue, workers, isolation.
7. **Review UI** — mapping tables, preview, approve/reject.

---

_This is a living document — expand each section as the project deepens._

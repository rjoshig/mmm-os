# Phase 9.1 — Source Abstraction & Landed Dataset

**Parent:** [`phase-09`](./phase-09-future-connectors-extraction.md) ·
**Depends on:** Phase 1 · **Status:** Foundational — **already realised in code**
(the Phase-1 source seam); documented here for the connector track.

## Objective

Define the source-agnostic ingestion abstraction so every inbound source produces
one common representation the whole pipeline consumes without knowing the source
(CC-9, ADR-010).

## Scope

- **In:** the `SourceConnector` contract (`test_connection` / `list_available` /
  `fetch`); the `LandedDataset` / `LandedTable` shape; source metadata
  (`source_type`, `source_ref`); `FileSource` as the first implementation.
- **Out:** any specific connector (SFTP/API) — later sub-phases.

## Functional Requirements

- **P9.1-1** A single `SourceConnector` contract every source implements.
- **P9.1-2** A common `LandedDataset` (tables + columns, or normalised records)
  tagged with `source_type ∈ {upload, sftp, api_connector}` and a `source_ref`.
- **P9.1-3** Downstream phases (mapping/transform/validation/output) consume the
  landed representation and never branch on source.
- **P9.1-4** Uploads realise the contract via `FileSource`, reusing Phase-1
  parsing/structure detection (no logic duplicated).

## Deliverables

- `src/mmm_os/sources/` — `base.py` (`SourceConnector`, `FetchRequest`),
  `landed.py` (`LandedDataset`, `LandedTable`), `file_source.py` (`FileSource`).
- `ingestion/process.py` routes structure detection through `FileSource`.
- `tests/test_sources.py`.

## Acceptance Criteria

- `FileSource.fetch` lands CSV + multi-tab XLSX into a `LandedDataset` (non-empty
  tables only), with `source_type`/`source_ref` set. **(Met.)**
- Existing Phase-1 processing/profiling behaviour is unchanged. **(Met.)**

## Dependencies

Phase 1 (parsing, structure detection, storage).

## Open Questions

None — foundational and realised.

## Sub-phases

N/A (leaf sub-phase).

---
name: document-ingestion
description: Handles Kitchen Assistant's documented CSV/TXT import and review-before-commit workflows. Use when parsing, validating, normalizing, previewing or confirming imported stock or sales data; OCR is out of MVP scope.
---

# Document Ingestion

## 1. Purpose

Make supported imports traceable and reviewable before they create inventory or sales records.

## 2. Activate when

- Working on the documented import of receipt/invoice-like input or sales/usage reports.
- Parsing CSV/TXT, validating rows, normalizing fields or showing an editable preview.
- Handling import errors, duplicate/rejected rows, user confirmation or auditability.

## 3. Do NOT activate when

- Implementing OCR, image/PDF recognition, handwriting recognition or invoice extraction from photos.
- Adding PaddleOCR, OpenCV or another OCR/document AI dependency.
- The file format or import contract is not specified by an authoritative source.

## 4. Required documents

- `mo_ta_chuc_nang_tro_ly_kho_bep.docx` — demo/function description; distinguishes implemented demo behavior from future backend requirements.
- `docs/architecture/architecture-revision-6.3.md`.
- `docs/implementation/implementation-plan.md`.
- `docs/architecture/ARCHITECTURE_REVISION_5.md` and Revision 3/4 contracts where available; verify paths.
- `PROJECT_CONTEXT.md` — required but unavailable during authoring.

## 5. Core rules

- The function description documents CSV/TXT input for import workflows, editable rows before confirmation, anomaly checking, and explicit confirmation before recording.
- The demo's image, PDF and Excel behavior uses sample data; it is not evidence of real OCR or production parsing for those formats.
- OCR invoice ingestion is **DEFERRED**. Do not implement or add OCR dependencies in the current MVP.
- The exact production parser contract, accepted CSV dialects, encoding rules, column mapping, duplicate policy, file size limits, upload storage, malware scanning and retry semantics are `NOT SPECIFIED` unless another approved source defines them.
- Separate parsing from committing. Parsing/preview must not mutate inventory or sales records.
- Validate structure, required values, numeric ranges, units and references against the approved contract. Do not silently coerce ambiguous values.
- Normalize units and data only using approved ingredient/base-unit conversion rules. Never invent a conversion factor.
- Preserve source-row identity and report which rows were accepted, rejected or changed. Do not claim traceability beyond what the implementation actually records.
- Require explicit user review/confirmation before committing imported business data, as described in the function flow.
- The final commit must use the approved backend service and transaction path; imported data must not bypass ledger, FEFO, costing, tenant or database invariants.
- Do not infer a new document schema, endpoint, status or idempotency key from the demo.

## 6. Recommended procedure

1. Confirm the requested format and import workflow are documented. If not, mark `NOT SPECIFIED`.
2. Inspect existing parser, document-line schema, API contract and tests before writing code.
3. Parse into a non-persistent preview representation.
4. Validate each row and produce actionable row-level errors/warnings.
5. Normalize only fields with an approved mapping or conversion rule.
6. Let the user review/edit the preview; preserve which values were changed where supported.
7. On explicit confirmation, submit through the approved backend transaction. Do not write directly to ledger tables from the parser.
8. Report commit outcome and row-level failures using actual evidence.

## 7. Validation checklist

- [ ] File format and workflow are approved and supported.
- [ ] Unsupported formats are rejected or clearly marked; no sample-data fallback is presented as real parsing.
- [ ] Parsing/preview does not mutate the database.
- [ ] Required fields, quantities, units and references are validated.
- [ ] Ambiguous conversions or mappings are not guessed.
- [ ] User can review and confirm before commit.
- [ ] Commit uses the approved service/transaction path.
- [ ] Ledger, FEFO, cost and kitchen-isolation safeguards remain active.
- [ ] Row-level errors and final result are accurately reported.
- [ ] No OCR feature or dependency entered the MVP.

## 8. Common mistakes

- Calling CSV/TXT demo parsing “AI OCR”.
- Treating sample PDF/image/Excel data as real extraction.
- Committing rows during preview.
- Silently dropping malformed rows or changing units.
- Guessing duplicate, encoding, column mapping or upload-size rules.
- Writing imported quantities directly into a stock cache.
- Adding OCR libraries despite Deferred scope.

## 9. Expected handoff

Provide supported formats, parser/normalization rules and their source, preview/confirmation behavior, row-level error examples, commit path, tests and evidence, unsupported formats, and all `NOT SPECIFIED` import decisions.

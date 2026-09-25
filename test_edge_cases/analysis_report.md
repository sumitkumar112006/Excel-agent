# Project analysis and current edge-case results

This report is based on a read-only review of the current source plus execution of the
fixture suite in this folder. No application source was changed.

## Current results

- Existing input set: 50 PDFs produced 51 records and all 51 were marked `PASS`.
- Edge-case suite: 200 separate PDFs, plus 2 fixture-integrity tests.
- Latest run: 202 tests, 177 errors and 3 assertion failures.
- The errors are themselves a critical finding: text-only/borderless PDFs reach the
  extractor's fallback path and crash before validation.

The three assertion-only fixture IDs are:

`095, 107, 170`

## Problems found

### Critical: fallback extraction crashes

1. `parse_all_product_items()` references `total_price_val` in the fallback branch
   before assigning it (`backend/extractor.py:840` and again at line 842). A borderless
   text PDF therefore raises `UnboundLocalError`; `process_single_pdf()` only catches
   errors while opening the PDF, not errors during parsing. The 177 erroring fixtures
   expose this immediately. Real PDFs can hide it when `page.find_tables()` succeeds.

### High priority: extraction can mark bad data as `PASS`

1. Missing consignee email/contact falls back to unrelated buyer or seller values. Cases
   081-084 demonstrate cross-section contamination.
2. Missing organisation, buyer, or paying-authority sections can still produce a `PASS`
   record by scanning the whole document. Cases 181-183 demonstrate insufficient section
   isolation.
3. Zero quantity, zero price, and zero total are repaired into positive values instead of
   remaining invalid. Cases 091, 101, and 107 demonstrate unsafe math backfilling.
4. Calendar-invalid dates such as day zero or day 32 are accepted because the date check
   is regex-only. Cases 033-034 demonstrate this.
5. Contract-number validation accepts any string containing `GEMC-` or `GEM-`, rather than
   validating the complete extracted value. The fallback can also capture the next label
   when the contract value is empty. Cases 021-030 demonstrate this.
6. Invalid GSTIN state/shape variants can still pass because the validator checks only a
   broad format, not the complete business validity rules. Cases 063-064 demonstrate this.
7. A blank or control-character-only document can inherit values from the fallback scan
   and receive an incorrect `PASS`. Cases 190 and 195-200 exercise this boundary.

### High priority: multi-product behavior is not reliable

Cases 141-150 and 157 expect one record per product, but the current stream fallback
collapses the fixture to one item. The implementation contains a single-item fallback
path in `backend/extractor.py`; the table path also depends on `page.find_tables()`, so
borderless multi-item text is especially vulnerable.

### Medium priority: normalization and layout gaps

1. Pipe-separated key/value text loses most fields; case 006 becomes `REVIEW`.
2. Comma-formatted quantities are not parsed consistently; case 095 becomes `REVIEW`.
3. Currency symbols such as `₹` are not normalized by the numeric converter; case 170
   becomes `REVIEW`.
4. Empty product names bleed the following `Brand` label into the product value; cases
   111 and 120 demonstrate label bleed.
5. Long or malformed address content can be accepted, rejected, or sanitized
   inconsistently; cases 071-080 cover this.
6. Filename contract fallback is blocked when an empty contract label first captures the
   next line as a value; cases 171 and 180 cover this.

### Storage/API problems found by source review

1. `storage_manager.save_batch_records()` writes `gem_contracts.xlsx` with
   `is_master=False`, so the file downloaded as the master workbook omits validation
   columns despite the code's own master-output documentation.
2. `save_and_append_records()` does not append; it delegates to a fresh batch overwrite.
   The name and older docstring are misleading and history is not preserved.
3. `clear_batch_json()` deletes `gem_contracts.json` and `records.jsonl` as well as the
   current-batch files. A UI “clear batch” action therefore removes the stored master
   data.
4. `/api/scan` always reports `already_processed: 0`, and `_run_extraction()` processes
   every PDF regardless of `reprocess_all`; the advertised incremental behavior is not
   implemented.
5. `/api/records` sets `total_master` equal to the filtered result count. Search and
   status filters therefore change the “master total” shown by the frontend.
6. Uploaded PDFs are copied into a new `pdfs/batch_*` folder and are not cleaned up after
   extraction, creating unbounded storage growth.

## Recommended fix order

1. Enforce section boundaries and treat empty/missing values as `NA` before any document-
   wide fallback.
2. Reject non-positive quantities/prices/totals and only backfill a missing value when
   the source explicitly provides the other two values.
3. Parse dates with `datetime` and validate the complete contract-number/GSTIN value.
4. Implement a deterministic line-item parser that returns one record per product and
   test it against cases 141-150 and 157.
5. Separate current-batch storage from historical/master storage and correct the master
   workbook/API totals.

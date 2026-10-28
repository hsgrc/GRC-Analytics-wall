# GetRightCover Chatbot Data Extract

This folder contains structured JSON data extracted from the uploaded Analytics Wall HTML and the Excel workbooks embedded inside it.

## Quick counts

- Customer Fleet profiles: **3,092**
- Customer-to-vehicle links: **22,357**
- Membership rows: **24,611**
- Renewal + Claims rows: **27,373**
- Vehicle compliance rows: **30,459**
- Raw vehicle portfolio rows (duplicates preserved): **30,659**
- RC status analysis rows: **1,729**
- Challan summary rows: **131 monthly, 30 state, 15 violation**

## File guide

- `customers.json`: customer profile and their source customer IDs.
- `customer_vehicle_links.json`: flat customer/vehicle relationship rows.
- `memberships.json`: membership records with customer, phone, vehicle, start/end dates, expiry bucket, membership type, Business Partner and vehicle type fields.
- `renewal_claims.json`: renewal records and `hasClaim` flag from the Renewal + Claims dashboard.
- `vehicles.json`: compliance-focused vehicle rows with insurance, PUC, fitness and tax expiry dates and flags.
- `vehicle_portfolio_records_raw.json`: raw vehicle portfolio source rows, including duplicates.
- `rc_statuses.json`: RC status analysis records, including the RC-related status columns.
- `challan_summaries.json`: aggregated challan statistics only.
- `insurance_summaries.json`: insurance-company aggregates and reconciliation workbook tables.
- `business_partners.json`: source-specific Business Partner records.
- `vehicle_lookup_index.json`: normalized registration lookup. Each `row_index` is a zero-based position in the referenced JSON file's top-level array.
- `phone_lookup_index.json`: phone-number lookup to source array indices. It is a lookup aid, not customer verification on its own.
- `customer_name_lookup_index.json`: normalized name lookup to source rows; combine with verified phone/customer ID to avoid name collisions.
- `renewal_summaries.json`, `vehicle_portfolio_summaries.json`: precomputed source dashboard summaries.
- `manifest.json`: source file list, counts and limitations.

## Important limitations

**Individual challans are not present in the uploaded Analytics Wall's embedded data.** The Challan Intelligence dashboard includes monthly/state/violation aggregates, but no individual vehicle-level e-challan/court-challan records. To answer “which challan is pending, what is its number, offence, amount or payment status?”, add the raw e-challan and court-challan exports as separate JSON datasets.

`hasClaim` in `renewal_claims.json` refers to a claim flag—not a challan flag. Do not use it to state that a challan exists.

Expiry flags in the dashboard are from the embedded data snapshot. The chatbot should calculate expiry status using each actual date field against the current date at query time, rather than relying only on a stale precomputed flag/bucket.

Customer names, mobile numbers and contact fields are personal data. In production, verify the customer and enforce customer-to-vehicle authorization before displaying any record. Keep this folder private; do not publish its JSON files as public static assets.

## Suggested local loading pattern

Load the small index files into memory once, then read only the relevant rows from the corresponding JSON arrays for each customer query. Do not send the complete 30k+ vehicle dataset to the language model in every prompt. Use deterministic code to find records, check ownership and compute expiry; give the local LLM only the verified, relevant result records.

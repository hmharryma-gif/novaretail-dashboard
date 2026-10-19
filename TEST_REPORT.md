# NovaRetail verification report

Verified on October 19, 2026 with Python 3.12 and the direct dependency versions in `requirements.txt`.

## Automated checks

**28 tests passed after the Dify integration update.** Run with:

```bash
python -m unittest discover -s tests -v
```

Coverage includes:

- Independent baseline values: $16,969.00 recorded revenue, 100 rows, 34 customer IDs, $169.69 average record amount and 3.71/5 mean satisfaction.
- All rows retained despite reused transaction IDs; Unknown retains $249.99.
- Overlapping customer membership between segments and original category names preserved.
- Date inclusion, combined filters, empty selections, one-day ranges and zero denominators.
- Mixed same-day labels and recency relative to the selected historical end date.
- Equal 14-day windows, exact boundaries, incomplete-window suppression, recent-only customers and customers with zero recent recorded spend.
- Changes to the low-satisfaction threshold and corresponding customer review reasons.
- Filtered chatbot evidence, valid JSON, anonymous session identifiers and clearing local history plus Dify conversation IDs when scope changes.
- No-key behavior, mocked successful Dify Chat Messages calls and follow-up conversation continuity, incomplete/blank/non-JSON responses and sanitized authentication/quota/connection failures.
- HTTPS endpoint validation, no authorization-bearing redirects, and credentials excluded from request evidence.
- Dify prompt variable and preview evidence, plus row-by-row equality of the cleaned CSV with the app's cleaned records.
- Actual Streamlit AppTest runs for initial rendering, five tabs, offline state, Growth-only filtering, no-match selections and a one-day selection.
- A Streamlit chat interaction using mocked Dify responses, followed by a Growth filter change and a new question. Verified that the request used $6,629.71 and omitted the previous conversation ID. Clear conversation was also verified.

## Running application and visual checks

The following browser checks were completed on the previous interface. The Dify update changes chatbot configuration text and transport, and was subsequently checked with Streamlit AppTest as described above. The unchanged chart layout was not retested in a browser.

- Started the actual Streamlit server and received HTTP 200 from its health endpoint.
- Used a headless Chromium browser to open the running app and navigate all five tabs.
- Inspected the desktop layout at 1440 × 1080 and mobile layout at 390 × 844.
- Confirmed the charts render, mobile sidebar collapses on initial load and the document does not overflow horizontally.
- Corrected top-of-page clipping and escaped dollar signs so two monetary amounts are not interpreted as a math expression.
- No browser page exceptions were recorded in the final run.

The wide tables allow their own horizontal scrolling. A local browser test is not a substitute for testing the public deployment URL.

## Dataset preservation

All 100 rows and 12 columns are unchanged from the supplied attachment. Exact equality was verified for every data value. The worksheet, shared-string table and cell-style XML are also byte-for-byte unchanged.

The packaged copy has been sanitized: author/editor names, personal cloud-storage location, editing timestamps and workbook revision identifiers were removed. Non-English fallback font-family names were replaced with their English aliases. The original supplied attachment was not modified.

The added `NR_dataset_cleaned.csv` retains all 100 records and 12 fields. Dates use YYYY-MM-DD, text is trimmed, and the missing segment is Unknown. It matches the app's cleaned data row by row, preserves $16,969.00 recorded revenue and contains no document-author metadata. A CSV preview was checked, and `DATA_CLEANING.md` documents unresolved source issues. The app still loads the original-value workbook to preserve the original-data audit.

SHA-256:

```text
30a4440eebfa11267875b90ff2ca31a7716cb0b5adeb07a0f085567476b1b190
```

## Language and identity review

- All published project text and filenames use English; the deployment guide is `DEPLOYMENT.md`.
- The AI instructions require English answers and prohibit disclosing project-owner or contributor identities.
- No owner name, email address, student identifier, personal account link, local device path or group number is included in the package.
- Workbook metadata was inspected inside the XLSX archive and sanitized as described above.
- Compiled caches, repository history, test screenshots, local logs and real credential files are excluded from the submission archive.
- Business-case role names and supplied customer/transaction identifiers remain part of the assignment data.

## Remaining external checks

**Live Dify UI tests completed on October 19, 2026.** NovaRetail Assistant was initially created and published using gpt-4.1-mini-2025-04-14 and the required `dashboard_context` Paragraph input (maximum 200000 characters). With the full preview JSON, the revised prompt correctly identified Growth revenue of $6,629.71 and Decline satisfaction of 1.58/5, with sample limitations. The initial responses overstated small-sample reliability and confused growth with retention priorities; the prompt was strengthened and retested.

The published web app was tested with a Growth-only KPI/segment fixture. It returned $6,629.71 and 11 distinct customer IDs and correctly declined to compare Decline without changing the evidence scope. These are live UI tests, not a live Streamlit-to-Dify API test. No app API key has been created or stored. Streamlit Secrets configuration and end-to-end API testing remain pending.

Dify chatbot: https://udify.app/chat/DsPerLgOY8NgFXc1
The standalone chatbot requires dashboard evidence input. This is not the required public Streamlit dashboard URL.

**Public deployment is pending.** No public URL is claimed. The code, workflow and deployment instructions are ready for publication. Repository ownership and commit-author metadata are configured separately from this package.

Before submission, publish the repository and Streamlit app, verify public access in a private browser window, test a real AI answer against the dashboard, fill the URL placeholder, and provide the contribution statement directly in the private submission form.

## Qwen model update

On October 19, 2026, the published model was changed to `qwen3.7-plus` (Tongyi) at the project requester's direction. A live Dify preview using the full dashboard evidence correctly returned Growth revenue of $6,629.71 (39.07%), Decline historical revenue of $3,649.81 (21.51%), mean satisfaction of 1.58, and 17 of 18 low-satisfaction records belonging to Decline. The answer noted small-sample and conflicting-identity limitations. Dify confirmed the published configuration was up to date. The earlier Growth-only public-chat test used the previous model; a live Streamlit-to-Dify API test remains pending.

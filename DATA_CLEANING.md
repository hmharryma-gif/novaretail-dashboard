# Cleaned dataset

`NR_dataset_cleaned.csv` contains the full dataset after the same cleaning applied by `app.py`. The source is `NR_dataset.xlsx`, worksheet `data`. The workbook retains its original data values and has identifying document metadata removed.

## Applied changes

- Retain all 100 records and the original 12 fields. Sort the export by `idx` to preserve the source record sequence.
- Trim surrounding whitespace in text fields.
- Replace the one missing segment with `Unknown`, retaining its $249.99 amount.
- Export dates consistently as `YYYY-MM-DD`.
- Validate that amounts are numeric, finite and non-negative, and ratings are integers from 1 through 5.
- Treat customer and transaction IDs as identifiers. Preserve their original values.
- Export monetary amounts to two decimal places. This preserves all source precision.

Control totals: 100 records, 34 distinct customer IDs, 25 distinct transaction IDs, 35 original category names and $16,969.00 recorded revenue. Dates cover January 15 through February 20, 2023.

## Unresolved source issues

The file is cleaned for consistent analysis, not certified as error-free. Reused transaction IDs, conflicting customer demographics and overlapping segment histories are retained because no authoritative corrections were supplied. No exact duplicate records were found after excluding `idx`. Do not deduplicate on transaction ID, infer 99 customers or assign every customer to one exclusive segment.

The 35 category labels remain separate. Similar-looking labels are not automatically merged into the five categories described in the background. Age and gender remain source columns for inspection but are excluded from dashboard targeting and chatbot evidence. Customer region is a record attribute, not a verified home location.

## Reproduce and use

Run `python export_cleaned_data.py` after installing `requirements.txt`. It regenerates the CSV and the full-selection preview context for Dify without making any API request.

The dashboard continues to load `NR_dataset.xlsx` so it can audit the original missing label. It applies the same cleaning before calculating metrics. The cleaned CSV is a portable analysis export; it does not replace the source audit.

For the Dify chatbot, use the dashboard's current computed evidence through `dashboard_context`. A static CSV uploaded to a knowledge base does not automatically follow Streamlit filters or guarantee correct whole-dataset totals from retrieved chunks.

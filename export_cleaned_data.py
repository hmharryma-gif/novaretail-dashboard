"""Export the same cleaned data used by the dashboard and a Dify preview fixture.

Run: python export_cleaned_data.py
The source workbook is never modified. No live API requests are made.
"""
import json

from app import ROOT, DIMENSIONS, build_evidence, customer_review, load_data


def main():
    data, audit = load_data()
    data.sort_values("idx").to_csv(ROOT / "NR_dataset_cleaned.csv", index=False,
                                   date_format="%Y-%m-%d", float_format="%.2f", encoding="utf-8-sig")
    start, end = data.TransactionDate.min().date(), data.TransactionDate.max().date()
    selections = {column: sorted(data[column].unique().tolist()) for column in DIMENSIONS.values()}
    scope = {"start": str(start), "end": str(end), "selections": selections,
             "low_satisfaction_cutoff": 2, "window_days": 14, "drop_cutoff_pct": 30}
    customers, period = customer_review(data, start, end)
    evidence = build_evidence(data, audit, scope, customers, period, 2, 30)
    (ROOT / "dify_preview_context.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=True, allow_nan=False) + "\n")
    print(f"Exported {len(data)} records; recorded revenue ${data.PurchaseAmount.sum():,.2f}.")


if __name__ == "__main__":
    main()

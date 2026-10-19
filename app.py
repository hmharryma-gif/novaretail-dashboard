"""NovaRetail Challenge 2. Run with: streamlit run app.py

All monetary metrics use source records, not purported unique orders. Pure
functions below are shared by the UI, AI evidence builder and automated tests.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import urlsplit
from uuid import uuid4

import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "NR_dataset.xlsx"
SEGMENTS = ["Growth", "Promising", "Stable", "Decline", "Unknown"]
COLORS = {"Growth": "#087F75", "Promising": "#3479B4", "Stable": "#8C7C54",
          "Decline": "#BF4B45", "Unknown": "#77838C", "Mixed": "#7D639B"}
DIMENSIONS = {"Segment": "label", "Region": "CustomerRegion",
              "Channel": "RetailChannel", "Product category": "ProductCategory"}
METRICS = {"Recorded revenue": "revenue", "Purchase records": "records",
           "Mean satisfaction": "satisfaction", "Average record amount": "average_amount"}
REQUIRED = ["idx", "label", "CustomerID", "TransactionID", "TransactionDate",
            "ProductCategory", "PurchaseAmount", "CustomerAgeGroup", "CustomerGender",
            "CustomerRegion", "CustomerSatisfaction", "RetailChannel"]


@st.cache_data(show_spinner=False)
def load_data(path: str = str(DATA_PATH)) -> tuple[pd.DataFrame, dict]:
    raw = pd.read_excel(path, sheet_name="data", engine="openpyxl")
    missing = set(REQUIRED) - set(raw.columns)
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))
    d = raw[REQUIRED].copy()
    audit = {"source_records": len(d), "observed_customer_ids": int(d.CustomerID.nunique()),
             "distinct_transaction_ids_not_orders": int(d.TransactionID.nunique()),
             "missing_segment_records": int(d.label.isna().sum()),
             "exact_duplicate_records_excluding_idx": int(d.duplicated([c for c in REQUIRED if c != "idx"]).sum()),
             "transaction_ids_shared_by_customers": int(d.groupby("TransactionID").CustomerID.nunique().gt(1).sum()),
             "transaction_ids_used_on_multiple_dates": int(d.groupby("TransactionID").TransactionDate.nunique().gt(1).sum())}
    for col in ["label", "CustomerAgeGroup", "CustomerGender", "CustomerRegion"]:
        audit[f"customer_ids_with_multiple_{col}"] = int(d.groupby("CustomerID")[col].nunique().gt(1).sum())
    for col in ["label", "TransactionID", "ProductCategory", "CustomerAgeGroup",
                "CustomerGender", "CustomerRegion", "RetailChannel"]:
        d[col] = d[col].astype("string").str.strip().fillna("Unknown").replace("", "Unknown")
    d["TransactionDate"] = pd.to_datetime(d.TransactionDate, errors="coerce").dt.normalize()
    d["PurchaseAmount"] = pd.to_numeric(d.PurchaseAmount, errors="coerce")
    d["CustomerSatisfaction"] = pd.to_numeric(d.CustomerSatisfaction, errors="coerce")
    if d[["TransactionDate", "PurchaseAmount", "CustomerID", "CustomerSatisfaction"]].isna().any().any():
        raise ValueError("Required date, amount, customer ID or satisfaction values are invalid. Review the source file.")
    if not np.isfinite(d.PurchaseAmount).all() or d.PurchaseAmount.lt(0).any():
        raise ValueError("PurchaseAmount must contain finite non-negative values for this dashboard.")
    if not d.CustomerSatisfaction.isin([1, 2, 3, 4, 5]).all():
        raise ValueError("Satisfaction must be an integer from 1 to 5.")
    if not d.label.isin(SEGMENTS).all():
        raise ValueError("Unrecognized segment labels. Review the source before extending the model.")
    d["CustomerID"] = d.CustomerID.astype(str)
    audit.update({"category_labels": int(d.ProductCategory.nunique()),
                  "date_start": str(d.TransactionDate.min().date()),
                  "date_end": str(d.TransactionDate.max().date()),
                  "recorded_revenue": round(float(d.PurchaseAmount.sum()), 2),
                  "same_day_customer_segment_conflicts": int(d.groupby(["CustomerID", "TransactionDate"]).label.nunique().gt(1).sum())})
    return d.sort_values(["TransactionDate", "idx"]).reset_index(drop=True), audit


def filter_data(d: pd.DataFrame, start, end, selections: dict) -> pd.DataFrame:
    mask = d.TransactionDate.between(pd.Timestamp(start), pd.Timestamp(end), inclusive="both")
    for column, values in selections.items():
        mask &= d[column].isin(values)
    return d.loc[mask].copy()


def kpis(d: pd.DataFrame) -> dict:
    revenue = round(float(d.PurchaseAmount.sum()), 2)
    decline = round(float(d.loc[d.label.eq("Decline"), "PurchaseAmount"].sum()), 2)
    return {"recorded_revenue": revenue, "records": len(d),
            "observed_customer_ids": int(d.CustomerID.nunique()),
            "average_record_amount": round(float(d.PurchaseAmount.mean()), 2) if len(d) else None,
            "mean_satisfaction": round(float(d.CustomerSatisfaction.mean()), 4) if len(d) else None,
            "decline_recorded_revenue": decline,
            "decline_revenue_share_pct": round(100 * decline / revenue, 4) if revenue else None}


def summary(d: pd.DataFrame, dimensions: str | list[str]) -> pd.DataFrame:
    result = d.groupby(dimensions, dropna=False, observed=True).agg(
        revenue=("PurchaseAmount", "sum"), records=("idx", "size"),
        customer_ids=("CustomerID", "nunique"), satisfaction=("CustomerSatisfaction", "mean"),
        average_amount=("PurchaseAmount", "mean")).reset_index()
    total = float(d.PurchaseAmount.sum())
    result["revenue_share_pct"] = result.revenue / total * 100 if total else np.nan
    return result.sort_values("revenue", ascending=False).reset_index(drop=True)


def period_comparison(d: pd.DataFrame, start, end, days: int) -> tuple[pd.DataFrame, dict]:
    start, end = pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize()
    recent_start = end - pd.Timedelta(days=days - 1)
    prior_end = recent_start - pd.Timedelta(days=1)
    prior_start = recent_start - pd.Timedelta(days=days)
    meta = {"available": bool(start <= prior_start), "window_days": days,
            "prior_start": str(prior_start.date()), "prior_end": str(prior_end.date()),
            "recent_start": str(recent_start.date()), "recent_end": str(end.date())}
    columns = ["CustomerID", "prior_revenue", "recent_revenue", "change_pct"]
    if not meta["available"]:
        return pd.DataFrame(columns=columns), meta
    prior = d.loc[d.TransactionDate.between(prior_start, prior_end)].groupby("CustomerID").PurchaseAmount.sum()
    recent = d.loc[d.TransactionDate.between(recent_start, end)].groupby("CustomerID").PurchaseAmount.sum()
    compare = pd.concat([prior.rename("prior_revenue"), recent.rename("recent_revenue")], axis=1).fillna(0)
    compare["change_pct"] = (compare.recent_revenue / compare.prior_revenue.replace(0, np.nan) - 1) * 100
    meta.update({"prior_recorded_revenue": round(float(prior.sum()), 2),
                 "recent_recorded_revenue": round(float(recent.sum()), 2),
                 "change_pct": round(float((recent.sum() / prior.sum() - 1) * 100), 4) if prior.sum() else None})
    return compare.reset_index()[columns], meta


def customer_review(d, start, end, days=14, low_cutoff=2, drop_cutoff=30):
    period, meta = period_comparison(d, start, end, days)
    rows = []
    for customer_id, group in d.groupby("CustomerID", sort=False):
        latest_date = group.TransactionDate.max()
        labels = sorted(group.loc[group.TransactionDate.eq(latest_date), "label"].unique())
        latest_label = labels[0] if len(labels) == 1 else "Mixed"
        low_count = int(group.CustomerSatisfaction.le(low_cutoff).sum())
        decline_count = int(group.label.eq("Decline").sum())
        rows.append({"CustomerID": customer_id, "revenue": float(group.PurchaseAmount.sum()),
                     "records": len(group), "satisfaction": float(group.CustomerSatisfaction.mean()),
                     "latest_segment": latest_label, "labels_observed": ", ".join(sorted(group.label.unique())),
                     "last_record_date": latest_date, "days_since_record": int((pd.Timestamp(end) - latest_date).days),
                     "low_satisfaction_records": low_count, "decline_records": decline_count})
    c = pd.DataFrame(rows)
    if c.empty:
        return c, meta
    c = c.merge(period, on="CustomerID", how="left")
    reasons = []
    for _, row in c.iterrows():
        signals = []
        if row.decline_records:
            signals.append("Decline-labeled record")
        if row.low_satisfaction_records:
            signals.append(f"Satisfaction <= {low_cutoff}")
        if pd.notna(row.change_pct) and row.change_pct <= -drop_cutoff:
            signals.append(f"Recorded spend down >= {drop_cutoff}%")
        reasons.append("; ".join(signals))
    c["review_reasons"] = reasons
    c["review_flag"] = c.review_reasons.ne("")
    return c.sort_values("revenue", ascending=False).reset_index(drop=True), meta


def records_json(df: pd.DataFrame) -> list:
    # pandas converts NaN/NaT to JSON null and timestamps to ISO dates.
    return json.loads(df.round(4).to_json(orient="records", date_format="iso"))


def build_evidence(d, audit, filters, customers, period, low_cutoff, drop_cutoff):
    low = d.loc[d.CustomerSatisfaction.le(low_cutoff)]
    return {"Scope": filters, "KPI": kpis(d), "Segments": records_json(summary(d, "label")),
            "Categories": records_json(summary(d, "ProductCategory")),
            "Regions": records_json(summary(d, "CustomerRegion")),
            "Channels": records_json(summary(d, "RetailChannel")),
            "Segment by channel": records_json(summary(d, ["label", "RetailChannel"])),
            "Category by channel": records_json(summary(d, ["ProductCategory", "RetailChannel"])),
            "Customers": records_json(customers), "Period": period,
            "Low satisfaction": {"threshold": low_cutoff, "records": len(low),
                                 "revenue": round(float(low.PurchaseAmount.sum()), 2),
                                 "segments": records_json(summary(low, "label"))},
            "Review settings": {"spend_drop_pct": drop_cutoff,
                                "flag_logic": "Any Decline record OR any low-satisfaction record OR period decline meeting threshold"},
            "Records": records_json(d.drop(columns=["CustomerAgeGroup", "CustomerGender"])),
            "Source quality": {"scope": "Full source workbook, unaffected by filters", **audit},
            "Limitations": "100 source rows and 34 observed customer IDs, not 99 confirmed consumers. IDs and segment histories conflict. No profit/cost data, validated churn outcomes or population sampling weights. Revenue shares and record-average satisfaction describe the selected sample only."}


def reset_chat_for_scope(state, scope):
    signature = hashlib.sha256(json.dumps(scope, sort_keys=True, default=str).encode()).hexdigest()
    if state.get("chat_scope") != signature:
        state["chat_scope"] = signature
        state["chat_history"] = []
        state["dify_conversation_id"] = ""
    return signature


class ChatServiceError(Exception):
    """A deliberately sanitized error that can be shown in the interface."""


def dify_error(status: int, code: str = "") -> ChatServiceError:
    if status in {401, 403}:
        message = "Dify authentication failed. Check the app API key in Streamlit Secrets."
    elif status == 429 or code in {"provider_quota_exceeded", "rate_limit_exceeded"}:
        message = "The Dify model quota or rate limit was reached. Check model credits or try again later."
    elif code in {"provider_not_initialize", "provider_not_initialized", "model_currently_not_support"}:
        message = "Configure an available chat model in Dify and publish the chatbot again."
    elif status == 404:
        message = "Dify could not find the app or conversation. Check DIFY_API_BASE and try Clear conversation."
    elif status == 400:
        message = "Dify rejected the request. Check that the published app is a Chatbot with a Paragraph variable named dashboard_context."
    else:
        message = "The Dify service could not complete this request. Try again later; no answer was generated."
    return ChatServiceError(message)


def ai_answer(question: str, evidence: dict, key: str, base_url: str,
              user_id: str, conversation_id: str = "", client=None) -> tuple[str, str]:
    """Call a Dify Chatbot from the server; keep credentials out of the payload."""
    if not key:
        raise ChatServiceError("AI is not connected. Configure DIFY_API_KEY in Streamlit Secrets.")
    base_url = base_url.strip().rstrip("/")
    try:
        parsed = urlsplit(base_url)
        valid_url = (parsed.scheme == "https" and parsed.hostname and not parsed.username
                     and not parsed.password and not parsed.query and not parsed.fragment)
    except ValueError:
        valid_url = False
    if not valid_url:
        raise ChatServiceError("DIFY_API_BASE must be an HTTPS API base URL without credentials or query parameters.")
    if not question.strip() or len(question) > 1500 or not user_id:
        raise ChatServiceError("Enter a question of 1 to 1,500 characters and try again.")
    payload = {"inputs": {"dashboard_context": json.dumps(evidence, ensure_ascii=True, allow_nan=False, separators=(",", ":"))},
               "query": question.strip(), "response_mode": "blocking", "user": user_id,
               "auto_generate_name": False}
    if conversation_id:
        payload["conversation_id"] = conversation_id
    response = (client or requests).post(
        base_url + "/chat-messages", headers={"Authorization": "Bearer " + key},
        json=payload, timeout=(10, 90), allow_redirects=False)
    try:
        body = response.json()
    except ValueError:
        raise dify_error(response.status_code) from None
    if not isinstance(body, dict):
        raise ChatServiceError("Dify returned an invalid response. No answer was accepted.")
    if response.status_code != 200 or body.get("event") == "error":
        raise dify_error(response.status_code, body.get("code", ""))
    answer, new_id = body.get("answer"), body.get("conversation_id")
    if body.get("event") != "message" or not isinstance(answer, str) or not answer.strip() or not isinstance(new_id, str) or not new_id:
        raise ChatServiceError("Dify returned an empty or incomplete reply. Try a narrower question.")
    return answer.strip(), new_id


def ai_error_message(exc: Exception) -> str:
    if isinstance(exc, ChatServiceError):
        return str(exc)
    if isinstance(exc, (requests.Timeout, requests.ConnectionError)):
        return "Dify could not be reached in time. The request may have reached the service; your dashboard data is still available."
    return "The Dify service could not complete this request. Try again later; no answer was generated."


def setting(name: str, default="") -> str:
    value = os.getenv(name)
    if value:
        return value
    try:
        return str(st.secrets.get(name, default))
    except (FileNotFoundError, KeyError):
        return default


def currency(value):
    return f"${value:,.2f}"


def display_markdown(text):
    """Keep monetary dollar signs literal instead of treating pairs as LaTeX."""
    return re.sub(r"(?<!\\)\$", r"\\$", text)


def chart(fig, key):
    fig.update_layout(font=dict(family="Arial, sans-serif", color="#142C3B", size=13),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      margin=dict(l=5, r=20, t=15, b=15), legend_title_text="",
                      hoverlabel=dict(bgcolor="white", font_color="#142C3B"))
    fig.update_xaxes(showgrid=True, gridcolor="#E6E5DF", zeroline=False)
    fig.update_yaxes(showgrid=False, zeroline=False)
    st.plotly_chart(fig, width="stretch", key=key, config={"displayModeBar": False})


def table(d, key=None):
    configs = {col: st.column_config.NumberColumn(col.replace("_", " ").title(), format="$%.2f")
               for col in ["revenue", "average_amount", "prior_revenue", "recent_revenue"] if col in d}
    configs.update({col: st.column_config.NumberColumn(col.replace("_", " ").title(), format="%.2f")
                    for col in ["satisfaction", "change_pct", "revenue_share_pct"] if col in d})
    st.dataframe(d, hide_index=True, width="stretch", column_config=configs, key=key)


def action_notes(d):
    k = kpis(d)
    growth = d.loc[d.label.isin(["Growth", "Promising"])]
    share = 100 * growth.PurchaseAmount.sum() / k["recorded_revenue"] if k["recorded_revenue"] else 0
    top = summary(d, "ProductCategory").iloc[0]
    low = d.loc[d.CustomerSatisfaction.le(2)]
    return [
        ("Develop existing demand", f"Growth + Promising records contribute {currency(growth.PurchaseAmount.sum())} ({share:.1f}%) in this selection. Pilot a targeted follow-up offer and compare repeat recorded spend with a holdout group."),
        ("Prioritize service recovery", f"{len(low)} records have satisfaction of 1 or 2. Decline-labeled records contribute {currency(k['decline_recorded_revenue'])}. Verify customer identity, then review low-rated experiences before offering blanket discounts."),
        ("Test the leading category", f"{top.ProductCategory} leads recorded revenue at {currency(top.revenue)} across {int(top.records)} records. Test a focused merchandising offer; compare incremental revenue and margin once cost data is available.")]


def draw_overview(d, customers):
    left, right = st.columns([1, 1.35], gap="large")
    with left:
        st.subheader("Revenue by segment")
        segments = summary(d, "label")
        fig = px.bar(segments, x="revenue", y="label", orientation="h", color="label",
                     color_discrete_map=COLORS, text="revenue", hover_data=["records", "satisfaction"],
                     labels={"revenue": "Recorded revenue (USD)", "label": ""})
        fig.update_traces(texttemplate="$%{x:,.0f}", textposition="outside", cliponaxis=False)
        fig.update_layout(showlegend=False, height=320)
        fig.update_yaxes(categoryorder="total ascending")
        fig.update_xaxes(range=[0, float(segments.revenue.max()) * 1.28], tickprefix="$")
        chart(fig, "segment_revenue")
        st.caption("Labels apply to records. Customer membership overlaps between segments.")
    with right:
        st.subheader("Daily recorded revenue")
        daily = d.groupby("TransactionDate").PurchaseAmount.sum().rename("revenue").reset_index()
        fig = px.bar(daily, x="TransactionDate", y="revenue", color_discrete_sequence=["#087F75"],
                     labels={"TransactionDate": "Record date", "revenue": "Recorded revenue (USD)"})
        fig.update_layout(height=320)
        fig.update_yaxes(showgrid=True, tickprefix="$")
        chart(fig, "daily_revenue")
        st.caption("Short sampled history. Gaps indicate no selected records, not confirmed zero company sales.")
    st.subheader("Decisions to explore")
    for col, (title, body) in zip(st.columns(3), action_notes(d)):
        with col:
            with st.container(border=True):
                st.markdown(f"**{title}**")
                st.write(body)
    st.subheader("Highest recorded spend by customer ID")
    top = customers.head(10).copy()
    total = float(d.PurchaseAmount.sum())
    top["revenue_share_pct"] = top.revenue / total * 100 if total else np.nan
    table(top[["CustomerID", "revenue", "revenue_share_pct", "records", "latest_segment", "satisfaction", "review_reasons"]])
    st.caption("Ranked within the current selection. Verify conflicting customer IDs before outreach.")


def draw_growth(d):
    st.subheader("Where to invest next")
    c1, c2, c3 = st.columns([1, 1, 1])
    dimension = c1.selectbox("Compare by", list(DIMENSIONS), index=3)
    metric = c2.selectbox("Rank by", list(METRICS))
    minimum = c3.number_input("Minimum records per group", min_value=1, max_value=max(1, len(d)), value=1)
    column, value = DIMENSIONS[dimension], METRICS[metric]
    groups = summary(d, column)
    shown = groups.loc[groups.records.ge(minimum)].sort_values(value, ascending=False)
    if shown.empty:
        st.info("No groups meet the minimum. Lower the minimum or expand the filters.")
    else:
        if len(shown) > 12:
            st.caption(f"Top 12 of {len(shown)} eligible groups shown; the table includes all eligible groups.")
        fig = px.bar(shown.head(12), x=value, y=column, orientation="h",
                     color_discrete_sequence=["#087F75"], hover_data=["records", "customer_ids"],
                     labels={value: metric, column: ""})
        fig.update_yaxes(categoryorder="total ascending")
        fig.update_layout(height=max(300, min(12, len(shown)) * 30 + 60))
        if value in {"revenue", "average_amount"}:
            fig.update_xaxes(tickprefix="$")
        elif value == "satisfaction":
            fig.update_xaxes(range=[0, 5])
        chart(fig, "opportunity_ranking")
        table(shown)
    st.subheader("Category and channel")
    pairs = summary(d, ["ProductCategory", "RetailChannel"])
    st.caption("All selected records. Zero cells mean no recorded revenue in this filtered sample. Original category names are preserved.")
    matrix = pairs.pivot(index="ProductCategory", columns="RetailChannel", values="revenue").fillna(0)
    matrix = matrix.loc[matrix.sum(axis=1).sort_values(ascending=False).index]
    table(matrix.reset_index())
    st.download_button("Download group analysis", shown.to_csv(index=False).encode("utf-8-sig"),
                       "novaretail_group_analysis.csv", "text/csv")
    st.info("Use volume and sample counts to choose a pilot. Revenue differences do not establish demand growth, campaign lift or profitability.")


def draw_retention(d, customers, period, low_cutoff, drop_cutoff):
    st.subheader("Signals for a retention review")
    low = d.loc[d.CustomerSatisfaction.le(low_cutoff)]
    decline = d.loc[d.label.eq("Decline")]
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Records rated ≤ {low_cutoff}", f"{len(low):,}")
    c2.metric("Decline-labeled revenue", currency(decline.PurchaseAmount.sum()))
    c3.metric("Customer IDs to review", str(int(customers.review_flag.sum())))
    st.caption(f"Review if any selected record has a Decline label, satisfaction ≤ {low_cutoff}, or recorded spend falls ≥ {drop_cutoff}% across the comparison windows. These are transparent review rules, not churn predictions.")
    a, b = st.columns(2, gap="large")
    with a:
        ratings = d.groupby(["label", "CustomerSatisfaction"]).size().reset_index(name="records")
        fig = px.bar(ratings, x="CustomerSatisfaction", y="records", color="label", color_discrete_map=COLORS,
                     labels={"CustomerSatisfaction": "Satisfaction (1–5)", "records": "Purchase records"})
        fig.update_xaxes(dtick=1, range=[0.5, 5.5])
        fig.update_layout(height=300, legend=dict(orientation="h", y=-0.3))
        chart(fig, "satisfaction_distribution")
    with b:
        st.markdown("**Equal-window spending comparison**")
        if period["available"]:
            st.write(f"Prior: {period['prior_start']} to {period['prior_end']}")
            st.write(f"Recent: {period['recent_start']} to {period['recent_end']}")
            st.markdown(display_markdown(f"Recorded revenue: **{currency(period['prior_recorded_revenue'])} → {currency(period['recent_recorded_revenue'])}**"))
            if period["change_pct"] is not None:
                st.write(f"Change: **{period['change_pct']:+.1f}%**")
            else:
                st.write("Change unavailable: prior recorded revenue is zero.")
            st.caption("Both windows use the same filters. No recent record is not proof of lost engagement. Data completeness and customer identity need confirmation.")
        else:
            st.info(f"Choose at least {2 * period['window_days']} calendar days to compare two complete windows. The comparison is unavailable for this selection.")
    only_flags = st.checkbox("Show only customer IDs requiring review", value=True)
    queue = customers.loc[customers.review_flag] if only_flags else customers
    cols = ["CustomerID", "revenue", "latest_segment", "last_record_date", "days_since_record",
            "low_satisfaction_records", "decline_records", "prior_revenue", "recent_revenue", "change_pct", "review_reasons"]
    table(queue[cols])
    st.caption("Recency ends at the selected date. Blank period values mean unavailable/not observed in either window; a zero within an observed window means no selected spend. A blank percentage means no positive prior base.")
    st.download_button("Download review queue", queue.to_csv(index=False).encode("utf-8-sig"),
                       "novaretail_retention_review.csv", "text/csv")
    with st.expander("Low-satisfaction records"):
        table(low.drop(columns=["CustomerAgeGroup", "CustomerGender"]))


def draw_methods(d, audit):
    st.subheader("Know what the data can support")
    st.warning(f"Full source audit: {audit['source_records']} rows, {audit['observed_customer_ids']} observed customer IDs, {audit['distinct_transaction_ids_not_orders']} distinct transaction IDs. The assignment describes 99 consumers; this workbook does not verify that count.")
    st.markdown("""All source rows are retained. The missing segment is **Unknown**. Transaction IDs are reused across dates and customers, so neither distinct IDs nor rows establish a verified order count. Multiple segment labels can belong to one customer on the same date.

Category and region analysis uses the values recorded on each row. Similar category names remain separate because no approved mapping was supplied. Age and gender are excluded from targeting because they conflict within customer IDs. The workbook covers a short sample; no population weights or profit costs are supplied.""")
    with st.expander("Full source quality checks", expanded=True):
        table(pd.DataFrame([{"Check": key.replace("_", " "), "Value": str(value)} for key, value in audit.items()]))
    st.markdown("""**Metric definitions**

| Metric | Definition |
|---|---|
| Recorded revenue | Sum of PurchaseAmount for selected source rows |
| Observed customer IDs | Distinct CustomerID values within the selection |
| Purchase records | Number of selected rows, not verified orders |
| Average record amount | Recorded revenue / selected row count |
| Mean satisfaction | Unweighted mean of selected 1–5 record ratings |
| Segment revenue share | Revenue on records with that label / all selected revenue, including Unknown |
| Latest segment | Label(s) on the latest selected date; Mixed if more than one |
| Days since record | Selected end date minus latest selected record date |
| Period spend change | (Recent recorded spend / prior recorded spend − 1) × 100; undefined for prior = 0 |

**Selected variables:** PurchaseAmount, TransactionDate, CustomerID, label, ProductCategory, CustomerRegion, RetailChannel and CustomerSatisfaction support the decisions. idx and TransactionID are retained for audit. Age and gender stay in the downloadable source, with no demographic targeting based on conflicting values.
""")
    st.subheader("Current filtered records")
    table(d.drop(columns=["CustomerAgeGroup", "CustomerGender"]))
    a, b = st.columns(2)
    a.download_button("Download filtered records", d.to_csv(index=False).encode("utf-8-sig"), "novaretail_filtered.csv", "text/csv")
    b.download_button("Download source dataset", DATA_PATH.read_bytes(), "NR_dataset.xlsx",
                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def draw_chat(evidence, d):
    st.subheader("Ask Nova")
    st.write("Ask about the current selection. Answers can reference revenue, segments, customer IDs and retention signals.")
    api_key = setting("DIFY_API_KEY")
    base_url = setting("DIFY_API_BASE", "https://api.dify.ai/v1")
    if "dify_user_id" not in st.session_state:
        st.session_state.dify_user_id = "novaretail-" + uuid4().hex
    code = setting("CHAT_ACCESS_CODE")
    unlocked = True
    if code:
        entered = st.text_input("Chat access code", type="password")
        unlocked = hmac.compare_digest(entered.encode(), code.encode())
    if api_key:
        st.caption("Dify configured. Questions and selected data are sent to Dify and its configured model when you submit. Verify answers against the evidence below.")
    else:
        st.info("AI is not connected. Add DIFY_API_KEY in Streamlit Secrets after publishing the Dify chatbot. See DIFY_SETUP.md for the required prompt and dashboard_context variable. The computed summaries below are not AI-generated.")
    with st.expander("Example questions", expanded=True):
        st.markdown("- Which customer IDs contribute the most recorded revenue?\n- Which segment should Sophia prioritize for service recovery?\n- How do the channels compare in this selection?\n- Suggest one growth experiment and cite the evidence.\n- What can we conclude about actual churn from this sample?")
    if not api_key:
        topic = st.selectbox("Computed summary (offline, not AI)", ["Overview", "Retention", "Channels", "Data quality"])
        if topic == "Overview":
            k = evidence["KPI"]
            st.write(f"{currency(k['recorded_revenue'])} across {k['records']} records and {k['observed_customer_ids']} observed customer IDs. [KPI]")
        elif topic == "Retention":
            low = evidence["Low satisfaction"]
            st.write(f"{low['records']} records are rated ≤ {low['threshold']}, representing {currency(low['revenue'])}. This is a review signal, not a churn prediction. [Low satisfaction]")
        elif topic == "Channels":
            table(summary(d, "RetailChannel"))
        else:
            st.write("Source audit: 100 rows, 34 observed customer IDs, one missing segment and reused transaction IDs. Customer-level interpretation needs validation. [Source quality]")
    for item in st.session_state.get("chat_history", []):
        with st.chat_message(item["role"]):
            st.markdown(display_markdown(item["content"]))
    if st.button("Clear conversation"):
        st.session_state.chat_history = []
        st.session_state.dify_conversation_id = ""
        st.rerun()
    count = st.session_state.get("ai_requests", 0)
    if count >= 20:
        st.info("The 20-question demo limit for this session has been reached.")
    question = st.chat_input("Ask a question about this selection…", disabled=not api_key or not unlocked or count >= 20, max_chars=1500)
    if question:
        if time.monotonic() - st.session_state.get("ai_last_request", 0) < 3:
            st.warning("Please wait a few seconds between questions.")
        else:
            st.session_state.ai_requests = count + 1
            st.session_state.ai_last_request = time.monotonic()
            with st.chat_message("user"):
                st.write(question)
            try:
                with st.spinner("Reading the selected data…"):
                    answer, conversation_id = ai_answer(
                        question, evidence, api_key, base_url, st.session_state.dify_user_id,
                        st.session_state.get("dify_conversation_id", ""))
                st.session_state.dify_conversation_id = conversation_id
                with st.chat_message("assistant"):
                    st.markdown(display_markdown(answer))
                st.session_state.chat_history.extend([{"role": "user", "content": question}, {"role": "assistant", "content": answer}])
            except Exception as exc:
                st.error(ai_error_message(exc))
    with st.expander("Evidence available to the assistant"):
        st.caption("These figures recalculate with the sidebar. Source quality is the only source-wide section. Changing filters or review settings starts a new conversation. Clearing chat here does not delete Dify's stored conversation logs.")
        st.json(evidence, expanded=False)
        st.download_button("Download current evidence", json.dumps(evidence, indent=2).encode(), "novaretail_chat_evidence.json", "application/json")


def main():
    st.set_page_config(page_title="NovaRetail | Customer Intelligence", page_icon="◈", layout="wide")
    st.markdown("""<style>
    .block-container {padding-top:4.2rem;padding-bottom:3rem;max-width:1500px}
    h1 {font-weight:750;letter-spacing:-1.4px;font-size:2.7rem!important}
    h2,h3 {letter-spacing:-.35px}
    [data-testid="stMetric"] {background:white;border:1px solid #E3E5DF;border-radius:12px;padding:14px 16px}
    [data-testid="stMetricValue"] {font-size:1.65rem!important;color:#142C3B}
    [data-testid="stMetricLabel"] {color:#526773}
    [data-testid="stSidebar"] {border-right:1px solid #E3E5DF}
    .eyebrow {font-size:.78rem;color:#087F75;letter-spacing:2px;font-weight:700;margin-bottom:.35rem}
    .stTabs [data-baseweb="tab"] {font-weight:600}
    @media(max-width:700px){h1{font-size:2rem!important}.block-container{padding:4rem 1rem 1rem}}
    </style>""", unsafe_allow_html=True)
    try:
        source, audit = load_data()
    except Exception as exc:
        st.error(f"Cannot load the dataset: {exc}")
        st.stop()
    low_date, high_date = source.TransactionDate.min().date(), source.TransactionDate.max().date()
    with st.sidebar:
        st.markdown("### NOVARETAIL")
        st.caption("CUSTOMER INTELLIGENCE")
        st.divider()
        st.markdown("**Explore your customer base**")
        def reset_filters():
            # Explicit values synchronize browser widgets; deleting keys can
            # reconnect a widget to its stale browser value on the next event.
            st.session_state["filter_dates"] = (low_date, high_date)
            for column in DIMENSIONS.values():
                options = SEGMENTS if column == "label" else sorted(source[column].unique())
                st.session_state[f"filter_{column}"] = list(options)
            st.session_state["low_cutoff"] = 2
            st.session_state["window_days"] = 14
            st.session_state["drop_cutoff"] = 30

        st.button("Reset filters", width="stretch", on_click=reset_filters)
        dates = st.date_input("Date range", (low_date, high_date), min_value=low_date, max_value=high_date,
                              format="YYYY-MM-DD", key="filter_dates")
        if len(dates) != 2:
            st.info("Choose an end date to complete the range.")
            st.stop()
        selections = {}
        for label, column in DIMENSIONS.items():
            options = SEGMENTS if column == "label" else sorted(source[column].unique())
            if column == "ProductCategory":
                with st.expander("Product categories"):
                    selections[column] = st.multiselect(label, options, default=options, key=f"filter_{column}")
                st.caption(f"{len(selections[column])} of {len(options)} product categories selected")
            else:
                selections[column] = st.multiselect(label, options, default=options, key=f"filter_{column}")
        with st.expander("Retention review settings"):
            low_cutoff = st.slider("Low satisfaction at or below", 1, 3, 2, key="low_cutoff")
            days = st.select_slider("Days per comparison window", [7, 14], value=14, key="window_days")
            drop_cutoff = st.slider("Recorded spend drop (%)", 10, 80, 30, step=10, key="drop_cutoff")
        st.caption("All filters intersect. Empty selections produce no results.")
    start, end = dates
    d = filter_data(source, start, end, selections)
    scope = {"start": str(start), "end": str(end), "selections": selections,
             "low_satisfaction_cutoff": low_cutoff, "window_days": days, "drop_cutoff_pct": drop_cutoff}
    reset_chat_for_scope(st.session_state, scope)
    st.markdown('<div class="eyebrow">NOVARETAIL / CUSTOMER INTELLIGENCE</div>', unsafe_allow_html=True)
    st.title("Customer insights. Clearer decisions.")
    st.write("Explore where revenue comes from, find opportunities and prioritize customer retention.")
    st.caption(f"SELECTED PERIOD  {start:%b %d, %Y} – {end:%b %d, %Y}  ·  {len(d)} of {len(source)} source records  ·  USD")
    st.info("Data note: 100 source records represent 34 observed customer IDs. Reused transaction IDs and conflicting customer attributes require validation. Revenue below is the sum of recorded amounts.")
    if d.empty:
        st.warning("No records match this selection. Expand the filters or choose Reset filters.")
        st.stop()
    k = kpis(d)
    for col, (label, value) in zip(st.columns(5), [
        ("Recorded revenue", currency(k["recorded_revenue"])),
        ("Observed customer IDs", f"{k['observed_customer_ids']:,}"),
        ("Purchase records", f"{k['records']:,}"),
        ("Average record amount", currency(k["average_record_amount"])),
        ("Mean satisfaction", f"{k['mean_satisfaction']:.2f} / 5")]):
        col.metric(label, value)
    st.write("")
    customers, period = customer_review(d, start, end, days, low_cutoff, drop_cutoff)
    tabs = st.tabs(["Overview", "Growth opportunities", "Retention review", "Data & methods", "AI assistant"])
    with tabs[0]:
        draw_overview(d, customers)
    with tabs[1]:
        draw_growth(d)
    with tabs[2]:
        draw_retention(d, customers, period, low_cutoff, drop_cutoff)
    with tabs[3]:
        draw_methods(d, audit)
    with tabs[4]:
        evidence = build_evidence(d, audit, scope, customers, period, low_cutoff, drop_cutoff)
        draw_chat(evidence, d)
    st.divider()
    st.caption("NovaRetail · Customer Intelligence · Historical sample: January–February 2023")


if __name__ == "__main__":
    main()

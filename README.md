# NovaRetail customer intelligence

Python / Streamlit / Plotly / Dify / Qwen

Live dashboard: https://novaretail-insights.streamlit.app/

Sophia Martinez needs to identify valuable customers, prioritize retention reviews and choose commercial experiments. This dashboard connects these decisions to the supplied workbook, with consistent filters and an AI assistant that receives the same selected data.

## Run locally

Use Python 3.12. From this folder:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

On Windows, activate with `.venv\Scripts\activate` instead. The dashboard and computed offline summaries work without API credentials. **Free-form AI requires a published Dify Chatbot, its app API key and an available model configured in Dify.** Follow `DIFY_SETUP.md`. Offline summaries alone do not satisfy the assignment's AI chatbot requirement.

## Files

| File | Purpose |
|---|---|
| `app.py` | Complete application, analytics and AI integration |
| `requirements.txt` | Tested, pinned direct dependencies |
| `NR_dataset.xlsx` | Supplied data with identifying document metadata removed; all data values preserved |
| `NR_dataset_cleaned.csv` | Portable cleaned export of all 100 records |
| `DATA_CLEANING.md` | Cleaning rules and unresolved source issues |
| `export_cleaned_data.py` | Reproduce the cleaned CSV and Dify preview evidence |
| `DIFY_SETUP.md` | Create, connect and verify the Dify chatbot |
| `dify_prompt.txt` | Prompt to paste into Dify |
| `dify_preview_context.json` | Full-selection evidence for testing in Dify Studio |
| `final_prompt.txt` | Final specification used to build this application |
| `BRIGHTSPACE_SUBMISSION.txt` | Three insights and the deployed dashboard URL |
| `dashboard_layout.svg` | Dashboard layout sketch |
| `DEPLOYMENT.md` | English deployment and submission instructions |
| `TEST_REPORT.md` | Automated and live verification results |
| `tests/test_dashboard.py` | Analytics, mocked AI and Streamlit interaction tests |
| `.streamlit/config.toml` | Theme and app settings |
| `.streamlit/secrets.toml.example` | Credential placeholders only |
| `.github/workflows/tests.yml` | Test workflow for GitHub |

## Deploy to GitHub and Streamlit Community Cloud

1. Create a GitHub repository, for example `novaretail-dashboard`, and upload this folder's contents to its root. Include the sanitized dataset and all required application files. Do not upload a real `secrets.toml`, `.env`, local virtual environment or credentials. The supplied `.gitignore` excludes these.
2. Sign in at [Streamlit Community Cloud](https://share.streamlit.io/) and connect the GitHub account/repository.
3. Create an app from the repository. Select the branch containing these files and set the entrypoint to `app.py`. Choose Python **3.12** in Advanced settings.
4. Complete `DIFY_SETUP.md`, then add the following in Streamlit's **Secrets** field, using the published Dify app's API key. Never put a real key in a public repository or the Brightspace note.

```toml
DIFY_API_KEY = "your-dify-app-api-key"
DIFY_API_BASE = "https://api.dify.ai/v1"
# Optional: enable a private class-demo code for the paid chat feature.
# CHAT_ACCESS_CODE = "your-private-demo-code"
```

Select and configure the chat model in Dify. The app needs a Paragraph variable named `dashboard_context` and the supplied `dify_prompt.txt`. Publish changes before testing. The deployed project uses Qwen3.7-plus through Dify; the live integration was verified on October 19, 2026. Model availability and remaining quota can change.

5. Deploy. Configure public app access in the app's share settings, then test the generated `https://…streamlit.app` URL in a private browser window.
6. Ask a real AI question, compare its cited numbers with the tables, change filters, and confirm the answer updates. Share the optional chat access code privately with the instructor if enabled. The dashboard itself remains accessible without it.
7. Paste the verified public URL into `BRIGHTSPACE_SUBMISSION.txt`. Provide the contribution statement directly in the private submission form; keep personal names out of this project. Upload `app.py`, `requirements.txt`, `NR_dataset.xlsx`, `final_prompt.txt` and the note to Brightspace.

The deployed application is available at https://novaretail-insights.streamlit.app/ with public sharing enabled. The source repository remains private; no real API key is included in these files.

## Layout and decisions

The persistent sidebar contains an inclusive date range, segment, region, channel and product-category filters plus retention settings. Empty selections return no records. The header shows the selected dates and record count, followed by five KPI cards.

| Tab | Main view | Decision supported |
|---|---|---|
| Overview | Segment revenue, daily amounts, action notes, highest-spend IDs | Prioritize customers and investigate concentration |
| Growth opportunities | Dimension/metric rankings, minimum group size, category/channel matrix | Choose a focused growth pilot |
| Retention review | Ratings, decline-labeled amounts, equal-window comparison, review queue | Investigate possible service and engagement issues |
| Data & methods | Source audit, definitions, selected records and downloads | Understand reliability and trace the calculations |
| AI assistant | Filter-aware free-form chat, examples, evidence download | Ask follow-up questions about the displayed data |

See `dashboard_layout.svg` for the sketch. CSV downloads use the current filters. The dataset download and source-quality audit are explicitly labeled full-source exceptions.

## Data choices and limitations

The workbook contains **100 records, 34 distinct CustomerID values, 25 distinct TransactionID values, and 35 original category names**, covering **January 15–February 20, 2023**. This conflicts with the assignment's stated 99 consumers.

- No exact duplicate records exist after excluding `idx`; all rows are retained.
- Nine transaction IDs are shared across different customer IDs. Ten occur on different dates. Distinct TransactionID is not a valid order count here.
- Ten customer IDs have multiple segment labels, including same-day conflicts. Segment charts use labels on records, not mutually exclusive customer groups.
- Ten customer IDs have multiple age groups and regions, and seven have multiple genders. Age and gender are excluded from targeting. Region is used as a recorded attribute, not a verified home location.
- One missing segment becomes **Unknown**, retaining its **$249.99**.
- Similar categories are not merged without an approved dictionary.
- Recorded revenue is the sum of amounts across rows. Total **$16,969.00** is an auditable source-row sum, not certified revenue from unique orders.
- Satisfaction is an unweighted record average. Customer counts overlap between groups. The sample does not establish population totals, profits, causation, actual churn probabilities or lifetime value.

The dashboard selects amount, date, customer ID, segment, category, region, channel and satisfaction for decisions. `idx` and `TransactionID` remain audit fields. All monetary outputs use USD.

## Language and identity

Project documentation, interface labels, source comments and chatbot responses are in English. The package contains no project-owner name, email address, student identifier, personal account link or local device path. Group identifiers have been removed from titles, filenames and suggested repository names. The workbook's author and personal-location metadata have been removed without changing dataset values. No credentials, compiled Python caches or repository history are included.

Sophia Martinez is the role named in the business case. CustomerID and TransactionID are dataset fields, not project-owner identifiers. User-entered chat messages and externally configured GitHub ownership, commit attribution and deployment account details are separate from the distributed project contents.

## Retention rules

A customer ID is flagged if any selected record is Decline-labeled, any selected record has satisfaction at or below the chosen cutoff (default 2), or its recent recorded spend is at least the chosen percentage below prior spend (default 30%). These are explicit review signals, not a fitted churn model. The queue is sorted by selected recorded revenue so reviewers can triage high-value IDs first.

The default comparison is the last 14 calendar days ending on the selected end date versus the preceding 14 days. It is suppressed if the date selection cannot contain both complete windows. Customers appearing in either window are retained. A customer with prior activity and no recent records gets zero recent recorded spend; recent-only customers have an undefined percentage change. Absence of records cannot establish churn because completeness and identity are unverified. Recency never uses today's date.

## AI implementation

Python computes the evidence first. The Streamlit server posts the current evidence as `inputs.dashboard_context` to Dify's `/chat-messages` endpoint. It includes selected source rows without age or gender, summary tables, filters, review settings and labeled source-wide quality checks. Dify controls the selected model and the system prompt. Paste the supplied `dify_prompt.txt` into the published Chatbot so it cites sections such as `[KPI]` and `[Segments]`, uses English and refuses unsupported claims. No agent or external tools are needed.

Each browser session receives a random anonymous identifier. Dify returns a conversation ID for follow-up questions. Changing filters or retention settings clears local history and starts a new Dify conversation. Clear conversation does the same. These actions do not delete existing Dify logs. Questions and selected sample data are sent to Dify and its configured model provider when submitted.

Requests have a 10-second connection timeout, 90-second read timeout and a 1,500-character question limit. Redirects and automatic retries are disabled. A timeout may occur after the service accepted a request. Credentials are sent only in the server's authorization header, never in the prompt, JSON evidence or browser interface. Missing keys, service errors, quota errors and empty or malformed replies produce clear errors instead of fabricated answers. The Dify model's output limit is configured in Dify Studio.

The 20-request session limit and optional chat code help control a class demo. They are **not a global spending cap** and browser sessions can restart. Review the Dify workspace's quota and model billing before public use.

## Reproduce the three insights

Start with **Reset filters** and the complete source period.

1. **Growth opportunity:** Overview shows Growth at $6,629.71 and Promising at $5,394.69, together $12,024.40 or 70.86% of recorded revenue. On Growth opportunities, compare Product category by Recorded revenue: Electronics leads with $7,089.84 across 16 records, or 41.78% of the sample. Test a focused campaign, without treating these descriptive results as proven growth.
2. **Retention:** Retention review with a low-satisfaction cutoff of 2 shows 19 Decline-labeled records totaling $3,649.81 (21.51% of all recorded revenue). Seventeen of these 19 records have satisfaction ≤2; their average across all 19 is 1.58/5. Verify identities and investigate service failures. The Unknown record also has satisfaction 1 and must remain visible.
3. **Commercial investment:** Growth opportunities → Compare by Channel. Physical Store has $9,515.50 and mean satisfaction 3.54; Online has $7,453.50 and 3.88, each from 50 records. Filter Segment to Decline and compare Channel: Physical Store contributes $2,619.89, or 71.78% of Decline-labeled recorded revenue. Test store service recovery before broad discounting, and evaluate repeat spend, satisfaction and margin when available.

## Classroom demonstration (about 4 minutes)

1. Reset filters, introduce the quality note, and show the five KPIs and highest-spend IDs.
2. In Growth opportunities, compare category and then channel. Explain sample counts.
3. Filter to Decline and Physical Store. Open Retention review and inspect the low-satisfaction records.
4. Open AI assistant. Ask: “What should Sophia prioritize in this selection, and which numbers support it?” Verify the cited evidence.
5. Reset filters, ask which IDs have highest recorded spend, and show that old chat history cleared. Mention the short sample and ID conflicts.

## Tests

```bash
python -m unittest discover -s tests -v
```

The tests do not call the paid API. See `TEST_REPORT.md` for the actual run and remaining publication checks.

## Official implementation references

- [Streamlit deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [Streamlit Secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)
- [Dify Chatbot configuration](https://docs.dify.ai/en/cloud/use-dify/build/chatbot)
- [Dify API setup](https://docs.dify.ai/en/api-reference/guides/get-started)
- [Dify Send Chat Message](https://docs.dify.ai/en/api-reference/chat-messages/send-chat-message)
- [Dify model providers](https://docs.dify.ai/en/cloud/use-dify/workspace/model-providers)

Business calculations use only the user-supplied `NR_dataset.xlsx`, sheet `data`.

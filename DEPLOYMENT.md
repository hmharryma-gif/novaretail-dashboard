# Deployment and submission

Deployed dashboard: https://novaretail-insights.streamlit.app/

The app runs on Streamlit Community Cloud with Python 3.12, public sharing enabled, and a Dify Qwen3.7-plus chatbot. The app API key is stored in Streamlit Secrets. See `TEST_REPORT.md` for live checks. The instructions below document how to reproduce the deployment.

## GitHub

Create a repository with a neutral name such as `novaretail-dashboard`. Upload the project files so `app.py`, `requirements.txt` and `NR_dataset.xlsx` are at the repository root.

`.streamlit/config.toml` controls the theme. `.streamlit/secrets.toml.example` contains placeholders and can be published. Never commit a real API key, `.env` file or `.streamlit/secrets.toml`.

Keep personal names, email addresses, student identifiers, personal account links and device paths out of the repository contents. Repository ownership and commit-author metadata are configured separately on GitHub; they are not anonymized by this project package.

## Streamlit Community Cloud

1. Open https://share.streamlit.io/ and connect the repository.
2. Create an app, select its branch, and set the main file path to `app.py`.
3. In Advanced settings, choose Python `3.12`.
4. Add these values to Streamlit Secrets, replacing only the API-key placeholder:

```toml
DIFY_API_KEY = "your-dify-app-api-key"
DIFY_API_BASE = "https://api.dify.ai/v1"
```

Configure the model inside Dify, add the Paragraph variable `dashboard_context`, paste `dify_prompt.txt`, and publish the Chatbot. Use the app API key, not a knowledge-base key or a model-provider key. Store the key in Streamlit Secrets, not in the repository or submission note.

5. Deploy and enable public access in the app's share settings.
6. Open the actual generated URL in a private browser window to verify access without signing in.
7. Ask a free-form AI question and compare the answer with the displayed figures.

Without a key, charts and explicitly labeled computed summaries remain available. Those summaries are not an AI chatbot and do not fulfill the live AI requirement.

Optionally set `CHAT_ACCESS_CODE` to restrict the paid chat feature while leaving the dashboard public. Share the code privately with the intended reviewer. The 20-request session limit is not an account-wide spending cap.

## Demonstration checks

- Reset filters: recorded revenue should be `$16,969.00`, observed customer IDs `34`, purchase records `100`, average record amount `$169.69`, and satisfaction `3.71 / 5`.
- Select only Growth: recorded revenue should become `$6,629.71`.
- Clear all segment selections: the app should show a no-results message.
- Ask: "Which customer IDs contribute the most recorded revenue?" Verify its cited evidence.
- Change filters: old chat history should clear, and the next answer should use the new scope.
- Check a filtered CSV download in Data & methods.

## Submission

Use `BRIGHTSPACE_SUBMISSION.txt` for the three insights. The verified deployment URL is already included. Supply the contribution declaration directly in the private submission form, without adding contributor names to this public project.

Submit `app.py`, `requirements.txt`, `NR_dataset.xlsx` and `final_prompt.txt` as required. Tests, documentation and the layout sketch are supporting project files.

## Data interpretation

The source contains 100 records and 34 different CustomerID values, although the assignment describes 99 consumers. Transaction IDs are reused and some customer attributes conflict. The dashboard preserves every data row, describes revenue as the sum of recorded amounts, and does not treat records as verified orders or assign every customer to one exclusive segment.

The packaged workbook has had author, personal-location and editing metadata removed. Dataset values and analytical results are preserved.

The optional `NR_dataset_cleaned.csv` contains the same cleaned records used by the app. See `DATA_CLEANING.md` for the cleaning decisions and `export_cleaned_data.py` to reproduce it. Keep `NR_dataset.xlsx` beside `app.py` because the application audits the original source values.

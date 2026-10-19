# Set up the NovaRetail chatbot in Dify

The Python dashboard calculates the figures. Dify supplies the conversational AI inside the dashboard's AI assistant tab. The Streamlit server sends the current selection to Dify with each question, so the chatbot has the same revenue and retention evidence as the charts.

## 1. Create the chatbot

1. Sign in at https://cloud.dify.ai/ and open Studio.
2. Choose Create from Blank and select **Chatbot**. Use the basic Chatbot type for this integration.
3. Name it **NovaRetail Assistant**. Use a neutral description: "Customer revenue, growth opportunities and retention review using dashboard evidence."
4. Select an available chat model in Dify. If none is available, open **Integrations > Model Provider** and configure one. Depending on the workspace, supported models can use Dify AI credits or a provider account. You do not need to choose OpenAI specifically.
5. If supported by the selected model, use low temperature (for example 0.2) and an output limit of about 1,024 tokens. Choose a model with enough context for the full preview evidence, the prompt, conversation history and output. If Dify reports a context limit, select a larger-context model.

Model choice and credentials belong in Dify. The Streamlit application uses the Dify app's key. These are different credentials.

## 2. Add the evidence variable and prompt

Add one input variable with these settings:

| Setting | Value |
|---|---|
| Variable name | `dashboard_context` |
| Field type | Paragraph |
| Label | Dashboard evidence |
| Required | Yes |
| Maximum length, if shown | 200,000 characters or an allowed value large enough for the evidence |

Paste the complete contents of `dify_prompt.txt` into the chatbot's Instructions/Prompt field. The final line contains `{{dashboard_context}}`. Insert it using Dify's variable picker if necessary, and confirm Dify recognizes the variable.

The prompt requires English answers, evidence references, accurate scope and limits on unsupported claims. Keep the app's file uploads, external tools and knowledge retrieval disabled for this setup. Its source is the dashboard evidence already supplied in the variable.

You do not need to upload the workbook to a knowledge base. A retrieved subset of a spreadsheet may omit rows needed for totals, and a static uploaded file does not automatically track Streamlit filters. `NR_dataset_cleaned.csv` is available for inspection and separate analysis.

## 3. Test in Dify Studio

Paste the contents of `dify_preview_context.json` into the Dashboard evidence input in the preview panel. This fixture represents the full dataset, not a live dashboard connection.

Ask these questions before publishing:

| Question | Reference answer for the full preview |
|---|---|
| What is total recorded revenue? | $16,969.00 across 100 records and 34 observed customer IDs |
| Which customer has the highest recorded revenue? | CustomerID 12351, $2,113.92 |
| Which segment contributes the most recorded revenue? | Growth, $6,629.71 |
| What early warning signs deserve review? | 19 Decline-labeled records total $3,649.81; 17 have satisfaction of 1 or 2 |
| What is our confirmed churn rate? | Not established by this sample |

Answers should cite sections such as `[KPI]`, `[Customers]` or `[Segments]`. Check the numbers, not exact wording. If a response claims 99 verified customers or treats repeated TransactionID values as orders, correct the prompt/configuration and retest.

## 4. Publish and connect to Streamlit

Click **Publish** after the preview works. Open the app's API access area and create an **app API key**. Dify UI versions may call this API Access, Access API, or expose it through the app's access settings. Use the app key, not a knowledge-base key, web-app URL, model-provider key or personal workspace credential.

In Streamlit Community Cloud, open **Advanced settings > Secrets** during deployment, or the existing app's **Settings > Secrets**, and enter:

```toml
DIFY_API_KEY = "your-dify-app-api-key"
DIFY_API_BASE = "https://api.dify.ai/v1"
```

For a self-hosted Dify instance, use its HTTPS API base URL instead. For local development, put the same settings in `.streamlit/secrets.toml`. The example file alone does not configure the app. Never commit the real key to GitHub or include it in the submission note.

Publish again whenever you change the Dify prompt, model or variables. The Streamlit dashboard is the main submitted application: https://novaretail-insights.streamlit.app/

## 5. Verify the integrated chatbot

1. In Streamlit, reset all filters and ask for total recorded revenue. Verify **$16,969.00**.
2. Ask a follow-up about the highest customer. Verify **12351** and **$2,113.92**.
3. Set Segment to **Growth**. Old conversation messages should disappear. Ask for revenue again and verify **$6,629.71**.
4. Clear the conversation and ask another question. The new conversation should still use the current Growth selection.
5. Restore all filters. Ask for confirmed churn or profit margin. The assistant should explain that the data cannot establish those figures.

Record the selected Dify model and the successful live checks in `TEST_REPORT.md` after testing. The deployed Streamlit integration has also returned live Qwen answers. See `TEST_REPORT.md` for the verified scope and figures.

## Troubleshooting

| Symptom | Check |
|---|---|
| AI is not connected | Set `DIFY_API_KEY` in the active Streamlit app's Secrets |
| Authentication failed | Use the key created for this Dify app |
| Dify rejected the request | Check Chatbot app type, Paragraph variable name and published prompt |
| Quota/model error | Check the selected model's configuration and credits in Dify |
| Blank or slow response | Try a shorter question or a faster available model; check Dify logs |
| Answer uses the previous selection | Change a filter or use Clear conversation; confirm the updated app.py is deployed |

The interface uses a random anonymous session identifier rather than a name or email. Questions and selected sample data are processed by Dify and its configured model provider. Clearing local conversation history does not erase Dify's logs. The project package contains no real keys or owner-identifying information.

## Official references

- Chatbot configuration: https://docs.dify.ai/en/cloud/use-dify/build/chatbot
- Model providers: https://docs.dify.ai/en/cloud/use-dify/workspace/model-providers
- API keys and base URL: https://docs.dify.ai/en/api-reference/guides/get-started
- Chat Messages API: https://docs.dify.ai/en/api-reference/chat-messages/send-chat-message
- End-user identifiers: https://docs.dify.ai/en/api-reference/guides/end-user-identity

## Current published model

NovaRetail Assistant uses `qwen3.7-plus` from Tongyi, selected and published in Dify on October 19, 2026. The Streamlit API integration does not require a model-name change: Dify applies the published model configuration. Model availability and credits are managed in Dify.

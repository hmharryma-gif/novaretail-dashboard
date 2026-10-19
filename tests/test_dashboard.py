"""Run: python -m unittest discover -s tests -v. No real API calls."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app


class AnalyticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d, cls.audit = app.load_data()

    def test_baseline_reconciles_without_deduplicating_ids(self):
        k = app.kpis(self.d)
        self.assertEqual(k["recorded_revenue"], 16969.00)
        self.assertEqual((k["records"], k["observed_customer_ids"]), (100, 34))
        self.assertEqual(k["average_record_amount"], 169.69)
        self.assertEqual(k["mean_satisfaction"], 3.71)
        self.assertEqual(self.audit["distinct_transaction_ids_not_orders"], 25)
        self.assertEqual(self.audit["exact_duplicate_records_excluding_idx"], 0)

    def test_missing_segment_keeps_its_amount(self):
        s = app.summary(self.d, "label").set_index("label")
        self.assertEqual(s.loc["Unknown", "records"], 1)
        self.assertAlmostEqual(s.loc["Unknown", "revenue"], 249.99)
        self.assertAlmostEqual(s.revenue.sum(), 16969.00)
        self.assertAlmostEqual(s.revenue_share_pct.sum(), 100)

    def test_segments_do_not_imply_exclusive_customers(self):
        s = app.summary(self.d, "label").set_index("label")
        self.assertAlmostEqual(s.loc["Growth", "revenue"], 6629.71)
        self.assertAlmostEqual(s.loc["Promising", "revenue"], 5394.69)
        self.assertGreater(s.customer_ids.sum(), 34)
        self.assertEqual(self.audit["same_day_customer_segment_conflicts"], 10)

    def test_original_category_names_are_preserved(self):
        s = app.summary(self.d, "ProductCategory").set_index("ProductCategory")
        self.assertEqual(len(s), 35)
        self.assertTrue({"Groceries", "Grocery", "Grocery Items"}.issubset(s.index))
        self.assertAlmostEqual(s.loc["Electronics", "revenue"], 7089.84)

    def test_intersecting_filters(self):
        d = app.filter_data(self.d, "2023-01-15", "2023-02-20", {
            "label": ["Growth"], "CustomerRegion": ["West"], "RetailChannel": ["Physical Store"]})
        self.assertEqual(len(d), 3)
        self.assertAlmostEqual(d.PurchaseAmount.sum(), 1049.97)

    def test_empty_selection_and_empty_kpis(self):
        d = app.filter_data(self.d, "2023-01-15", "2023-02-20", {"label": []})
        self.assertTrue(d.empty)
        k = app.kpis(d)
        self.assertEqual(k["recorded_revenue"], 0)
        self.assertIsNone(k["average_record_amount"])
        self.assertIsNone(k["mean_satisfaction"])

    def test_one_day_is_inclusive(self):
        d = app.filter_data(self.d, "2023-02-20", "2023-02-20", {})
        self.assertEqual(len(d), 1)
        self.assertAlmostEqual(d.PurchaseAmount.sum(), 199.99)

    def test_zero_revenue_share_not_infinity(self):
        d = self.d.iloc[:1].copy()
        d["PurchaseAmount"] = 0.0
        self.assertIsNone(app.kpis(d)["decline_revenue_share_pct"])
        self.assertTrue(app.summary(d, "label").revenue_share_pct.isna().all())

    def test_latest_same_day_labels_are_mixed(self):
        d = app.filter_data(self.d, "2023-01-20", "2023-01-20", {})
        c, _ = app.customer_review(d, "2023-01-20", "2023-01-20")
        self.assertEqual(c.iloc[0].latest_segment, "Mixed")
        self.assertEqual(c.iloc[0].days_since_record, 0)
        self.assertAlmostEqual(c.iloc[0].revenue, 859.94)

    def test_equal_windows_have_correct_dates_and_amounts(self):
        c, meta = app.period_comparison(self.d, "2023-01-15", "2023-02-20", 14)
        self.assertEqual((meta["prior_start"], meta["prior_end"]), ("2023-01-24", "2023-02-06"))
        self.assertEqual((meta["recent_start"], meta["recent_end"]), ("2023-02-07", "2023-02-20"))
        self.assertEqual(meta["prior_recorded_revenue"], 7434.53)
        self.assertEqual(meta["recent_recorded_revenue"], 4109.78)

    def test_partial_windows_are_suppressed(self):
        c, meta = app.period_comparison(self.d, "2023-01-25", "2023-02-20", 14)
        self.assertFalse(meta["available"])
        self.assertTrue(c.empty)
        _, exact = app.period_comparison(self.d, "2023-01-24", "2023-02-20", 14)
        self.assertTrue(exact["available"])

    def test_boundary_inclusion_new_and_inactive_customers(self):
        d = pd.DataFrame({"CustomerID": ["A", "A", "A", "A", "B", "C"],
                          "TransactionDate": pd.to_datetime(["2023-01-24", "2023-02-06", "2023-02-07", "2023-02-20", "2023-02-20", "2023-01-24"]),
                          "PurchaseAmount": [10, 20, 10, 20, 50, 40]})
        c, _ = app.period_comparison(d, "2023-01-24", "2023-02-20", 14)
        c = c.set_index("CustomerID")
        self.assertEqual(c.loc["A", "change_pct"], 0)
        self.assertTrue(pd.isna(c.loc["B", "change_pct"]))
        self.assertEqual(c.loc["C", "recent_revenue"], 0)
        self.assertEqual(c.loc["C", "change_pct"], -100)

    def test_recency_uses_selected_end(self):
        d = app.filter_data(self.d, "2023-01-15", "2023-01-31", {})
        c, _ = app.customer_review(d, "2023-01-15", "2023-01-31")
        self.assertEqual(c.set_index("CustomerID").loc["12345", "days_since_record"], 16)

    def test_threshold_change_affects_review_reasons(self):
        a, _ = app.customer_review(self.d, "2023-01-15", "2023-02-20", low_cutoff=1)
        b, _ = app.customer_review(self.d, "2023-01-15", "2023-02-20", low_cutoff=3)
        a, b = a.set_index("CustomerID"), b.set_index("CustomerID")
        self.assertEqual(a.loc["12350", "low_satisfaction_records"], 0)
        self.assertEqual(b.loc["12350", "low_satisfaction_records"], 1)

    def test_chat_evidence_is_filtered_and_serializable(self):
        d = app.filter_data(self.d, "2023-02-20", "2023-02-20", {"label": ["Growth"]})
        c, p = app.customer_review(d, "2023-02-20", "2023-02-20")
        evidence = app.build_evidence(d, self.audit, {"start": "2023-02-20"}, c, p, 2, 30)
        json.dumps(evidence, allow_nan=False)
        self.assertEqual(evidence["KPI"]["records"], 1)
        self.assertEqual(len(evidence["Records"]), 1)
        self.assertEqual(evidence["Categories"][0]["ProductCategory"], "Gaming")
        self.assertFalse(evidence["Period"]["available"])
        self.assertEqual(evidence["Source quality"]["source_records"], 100)
        self.assertNotIn("CustomerGender", evidence["Records"][0])


class ChatTests(unittest.TestCase):
    def test_scope_change_clears_stale_answers_but_not_rate_limit(self):
        state = {"ai_requests": 4}
        app.reset_chat_for_scope(state, {"region": "West"})
        state["chat_history"] = [{"role": "user", "content": "west"}]
        state["dify_conversation_id"] = "previous-conversation"
        app.reset_chat_for_scope(state, {"region": "West"})
        self.assertEqual(len(state["chat_history"]), 1)
        self.assertEqual(state["dify_conversation_id"], "previous-conversation")
        app.reset_chat_for_scope(state, {"region": "East"})
        self.assertEqual(state["chat_history"], [])
        self.assertEqual(state["dify_conversation_id"], "")
        self.assertEqual(state["ai_requests"], 4)

    def test_missing_key_makes_no_request(self):
        client = Mock()
        with self.assertRaises(app.ChatServiceError):
            app.ai_answer("revenue?", {}, "", "https://api.dify.ai/v1", "anonymous-test", client=client)
        client.post.assert_not_called()

    def test_real_interface_request_contract_with_mocked_response(self):
        client = Mock()
        client.post.return_value = Mock(status_code=200)
        client.post.return_value.json.return_value = {"event": "message", "answer": "$199.99 [KPI]", "conversation_id": "new-conversation"}
        evidence = {"KPI": {"recorded_revenue": 199.99}, "Scope": {"segment": "Growth"}}
        answer, conversation_id = app.ai_answer("revenue?", evidence, "unit-test-not-a-key", "https://api.dify.ai/v1/", "anonymous-test", client=client)
        args = client.post.call_args.kwargs
        self.assertIn("199.99", answer)
        self.assertEqual(conversation_id, "new-conversation")
        self.assertEqual(client.post.call_args.args[0], "https://api.dify.ai/v1/chat-messages")
        self.assertEqual(args["headers"]["Authorization"], "Bearer unit-test-not-a-key")
        self.assertNotIn("unit-test-not-a-key", json.dumps(args["json"]))
        self.assertEqual(json.loads(args["json"]["inputs"]["dashboard_context"]), evidence)
        self.assertEqual(args["json"]["response_mode"], "blocking")
        self.assertEqual(args["json"]["user"], "anonymous-test")
        self.assertNotIn("conversation_id", args["json"])
        self.assertFalse(args["json"]["auto_generate_name"])
        self.assertFalse(args["allow_redirects"])
        app.ai_answer("And satisfaction?", evidence, "unit-test-not-a-key", "https://api.dify.ai/v1", "anonymous-test", conversation_id, client)
        self.assertEqual(client.post.call_args.kwargs["json"]["conversation_id"], "new-conversation")

    def test_incomplete_or_blank_response_is_not_presented_as_answer(self):
        for body in [{"event": "message", "answer": "", "conversation_id": "test"},
                     {"event": "message", "answer": "partial"},
                     {"event": "error", "answer": "partial", "conversation_id": "test"},
                     ["unexpected response"]]:
            client = Mock()
            client.post.return_value = Mock(status_code=200)
            client.post.return_value.json.return_value = body
            with self.assertRaises(app.ChatServiceError):
                app.ai_answer("revenue?", {}, "test", "https://api.dify.ai/v1", "anonymous-test", client=client)

    def test_api_errors_do_not_expose_raw_details(self):
        for status in [400, 401, 403, 404, 429, 500, 302]:
            client = Mock()
            client.post.return_value = Mock(status_code=status)
            client.post.return_value.json.return_value = {"message": "SENSITIVE_RAW_DETAIL"}
            with self.assertRaises(app.ChatServiceError) as error:
                app.ai_answer("revenue?", {}, "test", "https://api.dify.ai/v1", "anonymous-test", client=client)
            self.assertNotIn("SENSITIVE_RAW_DETAIL", app.ai_error_message(error.exception))
        for exc in [requests.ConnectionError("SENSITIVE_RAW_DETAIL"), requests.Timeout("SENSITIVE_RAW_DETAIL"), ValueError("SENSITIVE_RAW_DETAIL")]:
            self.assertNotIn("SENSITIVE_RAW_DETAIL", app.ai_error_message(exc))

    def test_invalid_endpoint_rejects_before_sending_key(self):
        for url in ["http://api.dify.ai/v1", "https://user:password@api.dify.ai/v1", "https://api.dify.ai/v1?key=value"]:
            client = Mock()
            with self.assertRaises(app.ChatServiceError):
                app.ai_answer("revenue?", {}, "test", url, "anonymous-test", client=client)
            client.post.assert_not_called()

    def test_non_json_response_is_sanitized(self):
        client = Mock()
        client.post.return_value = Mock(status_code=502)
        client.post.return_value.json.side_effect = ValueError("SENSITIVE_RAW_DETAIL")
        with self.assertRaises(app.ChatServiceError) as error:
            app.ai_answer("revenue?", {}, "test", "https://api.dify.ai/v1", "anonymous-test", client=client)
        self.assertNotIn("SENSITIVE_RAW_DETAIL", str(error.exception))

    def test_prompt_and_preview_match_required_variable_and_data(self):
        prompt = (app.ROOT / "dify_prompt.txt").read_text()
        self.assertIn("{{dashboard_context}}", prompt)
        self.assertIn("English", prompt)
        preview = json.loads((app.ROOT / "dify_preview_context.json").read_text())
        self.assertEqual(preview["KPI"]["recorded_revenue"], 16969.00)
        self.assertEqual(len(preview["Records"]), 100)

    def test_cleaned_csv_retains_rows_amounts_and_unknown(self):
        clean = pd.read_csv(app.ROOT / "NR_dataset_cleaned.csv", dtype={"CustomerID": str, "TransactionID": str})
        self.assertEqual(clean.shape, (100, 12))
        self.assertEqual(clean.CustomerID.nunique(), 34)
        self.assertAlmostEqual(clean.PurchaseAmount.sum(), 16969.00)
        self.assertEqual(clean.label.eq("Unknown").sum(), 1)
        self.assertTrue(clean.TransactionDate.str.fullmatch(r"\d{4}-\d{2}-\d{2}").all())
        source, _ = app.load_data()
        pd.testing.assert_frame_equal(clean.sort_values("idx").reset_index(drop=True),
            source.assign(TransactionDate=source.TransactionDate.dt.strftime("%Y-%m-%d")).sort_values("idx").reset_index(drop=True),
            check_dtype=False)


class StreamlitTests(unittest.TestCase):
    def setUp(self):
        from streamlit.testing.v1 import AppTest
        self.at = AppTest.from_file(str(app.ROOT / "app.py"), default_timeout=30)

    @patch.dict("os.environ", {"DIFY_API_KEY": "", "CHAT_ACCESS_CODE": ""})
    def test_app_renders_all_tabs_and_offline_state(self):
        self.at.run()
        self.assertEqual(len(self.at.exception), 0)
        self.assertEqual(self.at.metric[0].value, "$16,969.00")
        self.assertEqual(len(self.at.tabs), 5)
        self.assertTrue(any("AI is not connected" in item.value for item in self.at.info))

    @patch.dict("os.environ", {"DIFY_API_KEY": "unit-test-not-a-key", "DIFY_API_BASE": "https://api.dify.ai/v1", "CHAT_ACCESS_CODE": ""})
    @patch("requests.post")
    def test_dify_chat_uses_current_scope_and_resets_conversation(self, post):
        post.return_value = Mock(status_code=200)
        post.return_value.json.return_value = {"event": "message", "answer": "$16,969.00 [KPI]", "conversation_id": "first-conversation"}
        self.at.run()
        self.at.chat_input[0].set_value("What is revenue?").run()
        self.assertEqual(len(self.at.exception), 0)
        self.assertEqual(self.at.session_state["dify_conversation_id"], "first-conversation")
        user_id = post.call_args.kwargs["json"]["user"]
        self.assertRegex(user_id, r"^novaretail-[a-f0-9]{32}$")
        self.at.multiselect(key="filter_label").set_value(["Growth"]).run()
        self.assertEqual(self.at.session_state["dify_conversation_id"], "")
        self.assertEqual(self.at.session_state["chat_history"], [])
        self.at.session_state["ai_last_request"] = 0
        post.return_value.json.return_value = {"event": "message", "answer": "$6,629.71 [KPI]", "conversation_id": "growth-conversation"}
        self.at.chat_input[0].set_value("What is revenue now?").run()
        payload = post.call_args.kwargs["json"]
        self.assertEqual(json.loads(payload["inputs"]["dashboard_context"])["KPI"]["recorded_revenue"], 6629.71)
        self.assertNotIn("conversation_id", payload)
        self.assertEqual(payload["user"], user_id)
        self.assertEqual(len(self.at.exception), 0)
        next(button for button in self.at.button if button.label == "Clear conversation").click().run()
        self.assertEqual(self.at.session_state["dify_conversation_id"], "")
        self.assertEqual(self.at.session_state["chat_history"], [])

    def test_ui_filters_and_empty_state(self):
        self.at.run()
        self.at.multiselect(key="filter_label").set_value(["Growth"]).run()
        self.assertEqual(len(self.at.exception), 0)
        self.assertEqual(self.at.metric[0].value, "$6,629.71")
        self.at.multiselect(key="filter_label").set_value([]).run()
        self.assertEqual(len(self.at.exception), 0)
        self.assertTrue(any("No records match" in item.value for item in self.at.warning))

    def test_one_day_ui_and_short_period(self):
        from datetime import date
        self.at.run()
        self.at.date_input(key="filter_dates").set_value((date(2023, 2, 20), date(2023, 2, 20))).run()
        self.assertEqual(len(self.at.exception), 0)
        self.assertEqual(self.at.metric[0].value, "$199.99")
        self.assertTrue(any("two complete windows" in item.value for item in self.at.info))


if __name__ == "__main__":
    unittest.main()

import importlib
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


def _fake_pipeline(task, model=None, top_k=None):
    if task == "text-classification":
        def classify(text):
            lowered = text.lower()
            if "stress" in lowered or "anx" in lowered:
                label = "fear"
            elif "happy" in lowered or "great" in lowered:
                label = "joy"
            elif "angry" in lowered or "nerves" in lowered:
                label = "anger"
            else:
                label = "sadness"
            return [[{"label": label, "score": 0.98}]]
        return classify

    if task == "zero-shot-classification":
        def classify(text, labels):
            lowered = text.lower()
            if "bye" in lowered:
                label = "saying goodbye"
            elif "help" in lowered or "advice" in lowered or "what should i do" in lowered:
                label = "asking for advice"
            elif "happy" in lowered or "great" in lowered:
                label = "sharing something positive"
            else:
                label = "general conversation"
            return {"labels": [label]}
        return classify

    raise ValueError(f"Unexpected pipeline task: {task}")


class WellnessPlatformTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fake_transformers = types.ModuleType("transformers")
        fake_transformers.pipeline = _fake_pipeline
        sys.modules["transformers"] = fake_transformers

        for module_name in ["model", "response_generator", "app"]:
            sys.modules.pop(module_name, None)

        cls.model = importlib.import_module("model")
        cls.response_generator = importlib.import_module("response_generator")
        cls.app_module = importlib.import_module("app")
        cls.client = cls.app_module.app.test_client()

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.app_module.DATA_DIR = Path(self.temp_dir)
        self.app_module.DATA_FILE = self.app_module.DATA_DIR / "wellness_data.json"
        self.app_module.ensure_storage()
        self.app_module.save_data({"moods": [], "journals": []})

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_map_emotion_groups_labels(self):
        self.assertEqual(self.model.map_emotion("grief"), "sadness")
        self.assertEqual(self.model.map_emotion("fear"), "anxiety")
        self.assertEqual(self.model.map_emotion("joy"), "positive")
        self.assertEqual(self.model.map_emotion("surprise"), "neutral")

    def test_detect_crisis_matches_expanded_phrases(self):
        self.assertTrue(self.model.detect_crisis("I want to hurt myself tonight"))
        self.assertTrue(self.model.detect_crisis("Sometimes I feel better off dead"))
        self.assertFalse(self.model.detect_crisis("I had a difficult exam today"))

    def test_generate_response_ends_on_closing_message(self):
        reply = self.response_generator.generate_response(
            emotion="neutral",
            intent="general conversation",
            crisis=False,
            user_message="no",
            conversation_history=[{"user": "i had ice cream", "bot": "What stood out the most?"}],
        )
        self.assertTrue("take care" in reply.lower() or "leave it here" in reply.lower())

    def test_dashboard_page_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Your wellness space", response.data)

    def test_chat_page_loads(self):
        response = self.client.get("/chat")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Chat Support", response.data)

    def test_dashboard_api_returns_stats(self):
        response = self.client.get("/api/dashboard")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("stats", payload)
        self.assertEqual(payload["stats"]["total_check_ins"], 0)

    def test_post_mood_entry_persists_data(self):
        response = self.client.post("/api/moods", json={"mood": "anxiety", "note": "Exam week pressure"})
        self.assertEqual(response.status_code, 201)
        payload = response.get_json()
        self.assertEqual(payload["entry"]["mood"], "anxiety")

        stored = self.app_module.load_data()
        self.assertEqual(len(stored["moods"]), 1)
        self.assertEqual(stored["moods"][0]["note"], "Exam week pressure")

    def test_post_journal_entry_persists_data(self):
        response = self.client.post(
            "/api/journals",
            json={"title": "Heavy morning", "content": "I felt off and needed a pause.", "emotion": "sadness"},
        )
        self.assertEqual(response.status_code, 201)
        stored = self.app_module.load_data()
        self.assertEqual(len(stored["journals"]), 1)
        self.assertEqual(stored["journals"][0]["title"], "Heavy morning")

    def test_chat_api_returns_expected_fields(self):
        response = self.client.post(
            "/api/chat",
            json={
                "message": "I need help with stress",
                "conversation_history": [],
                "emotion_history": [],
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("response", payload)
        self.assertIn("emotion", payload)
        self.assertIn("mood_summary", payload)
        self.assertFalse(payload["crisis"])

    def test_chat_api_rejects_empty_message(self):
        response = self.client.post("/api/chat", json={"message": "   "})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())

    def test_chat_api_generates_crisis_response(self):
        response = self.client.post(
            "/api/chat",
            json={"message": "I want to end my life", "conversation_history": [], "emotion_history": []},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["crisis"])
        self.assertIn("988", payload["response"])

    def test_insights_api_reflects_saved_entries(self):
        self.client.post("/api/moods", json={"mood": "sadness", "note": "Rough day"})
        self.client.post(
            "/api/journals",
            json={"title": "After work", "content": "Everything felt heavy today.", "emotion": "sadness"},
        )

        response = self.client.get("/api/insights")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["dominant_mood"], "Low")
        self.assertGreaterEqual(len(payload["recent_notes"]), 1)

    def test_tools_api_returns_support_tools(self):
        response = self.client.get("/api/tools")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertGreaterEqual(len(payload["tools"]), 3)
        self.assertGreaterEqual(len(payload["crisis_resources"]), 3)

    def test_compute_streak_counts_consecutive_days(self):
        streak = self.app_module.compute_streak(
            [
                {"date": "2026-04-20"},
                {"date": "2026-04-19"},
                {"date": "2026-04-18"},
            ]
        )
        self.assertEqual(streak, 3)

    def test_generate_response_avoids_repeating_previous_message(self):
        previous = "That sounds like a bright moment. What stood out the most?"
        reply = self.response_generator.generate_response(
            emotion="positive",
            intent="sharing something positive",
            crisis=False,
            user_message="I had a nice walk",
            conversation_history=[{"user": "I feel good", "bot": previous}],
        )
        self.assertNotEqual(reply, previous)

    def test_generate_response_does_not_treat_short_positive_followup_as_advice(self):
        with patch.object(self.response_generator.random, "choice", side_effect=lambda options: options[0]):
            reply = self.response_generator.generate_response(
                emotion="neutral",
                intent="asking for advice",
                crisis=False,
                user_message="taking this ppt",
                conversation_history=[
                    {
                        "user": "happy",
                        "bot": "That's really good to hear. What made this feel meaningful for you?",
                    }
                ],
            )
        self.assertIn("added to the good feeling", reply.lower())
        self.assertNotIn("we can think it through together", reply.lower())

    def test_python_files_compile(self):
        import py_compile

        py_compile.compile("app.py", doraise=True)
        py_compile.compile("model.py", doraise=True)
        py_compile.compile("response_generator.py", doraise=True)


if __name__ == "__main__":
    unittest.main()

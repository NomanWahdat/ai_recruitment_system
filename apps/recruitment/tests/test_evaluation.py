import io
import json
import runpy
import sys
import tempfile
from contextlib import redirect_stderr
from copy import deepcopy
from datetime import date
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APITestCase

from apps.recruitment.services.evaluation import (
    evaluate_dataset,
    extraction_metrics,
    intervals,
    ranking_metrics,
    validate_dataset,
    weighted_kappa,
)
from apps.recruitment.services.experience_extractor import ExperienceExtractor


class EvaluationTests(SimpleTestCase):
    def setUp(self):
        self.dataset = json.loads(
            (settings.BASE_DIR / "evaluation/dataset.json").read_text(encoding="utf-8")
        )

    def evaluate(self, dataset, **options):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "labels.json"
            path.write_bytes(json.dumps(dataset).encode("utf-8"))
            return evaluate_dataset(path, **options)

    def test_metrics_have_known_correct_values(self):
        cases = [
            {
                "true_positive_skills": 1,
                "unexpected_skills": ["x"],
                "missing_skills": ["y"],
                "email_correct": True,
                "experience_absolute_error": 2,
            },
            {
                "true_positive_skills": 0,
                "unexpected_skills": [],
                "missing_skills": [],
                "email_correct": False,
                "experience_absolute_error": 0,
            },
        ]
        metrics = extraction_metrics(cases)
        self.assertEqual(metrics["skill_f1"], 0.5)
        self.assertEqual(metrics["email_accuracy"], 0.5)
        self.assertEqual(metrics["experience_mae_years"], 1)
        self.assertEqual(intervals(cases), intervals(cases))

    def test_ranking_metrics_reward_relevant_results(self):
        ideal = ranking_metrics([0, 1, 2], [3, 2, 0], 1)
        reverse = ranking_metrics([2, 1, 0], [3, 2, 0], 1)
        self.assertEqual(ideal["ndcg_at_k"], 1)
        self.assertEqual(ideal["recall_at_k"], 0.5)
        self.assertEqual(ideal["mrr"], 1)
        self.assertLess(reverse["ndcg_at_k"], ideal["ndcg_at_k"])
        self.assertIsNone(ranking_metrics([0], [0], 1)["recall_at_k"])

    def test_invalid_and_duplicate_labels_are_rejected(self):
        for mutate in [
            lambda d: d["records"][0].update(years=float("nan")),
            lambda d: d["records"][0].update(grades=[4, 0]),
            lambda d: d["records"][0].update(grades=[1]),
            lambda d: d["records"][0].update(split="heldout-unknown"),
            lambda d: d["records"].append(deepcopy(d["records"][0])),
            lambda d: d["jobs"][0].update(scoring_weights={"skills": 1}),
            lambda d: d["records"][0].update(ratings=[[1, 0]]),
        ]:
            dataset = deepcopy(self.dataset)
            mutate(dataset)
            with self.assertRaises(ValueError):
                validate_dataset(dataset)

    @override_settings(USE_LLM_FOR_SCORING=True, USE_GROQ_AI=True, GROQ_API_KEY="synthetic")
    def test_offline_mode_never_calls_providers_and_reports_failures(self):
        with patch("requests.post") as post:
            report = self.evaluate(self.dataset)
        post.assert_not_called()
        self.assertEqual(report["external_requests"], 0)
        self.assertEqual(report["records"], 24)
        self.assertEqual(report["by_split"]["regression"]["records"], 12)
        self.assertTrue(report["checks"]["passed"])
        self.assertTrue(report["failure_cases"])
        self.assertLess(report["by_split"]["challenge"]["skill_f1"], 1)
        self.assertFalse(report["independence_verified"])

    def test_split_and_fixed_reference_date(self):
        report = self.evaluate(self.dataset, split="regression")
        self.assertEqual(report["records"], 12)
        self.assertEqual(set(report["by_split"]), {"regression"})
        extractor = ExperienceExtractor(as_of=date(2026, 10, 27))
        self.assertEqual(float(extractor.estimate("Experience\nJan 2025 - Present")), 1.8)
        with self.assertRaises(ValueError):
            self.evaluate(self.dataset, split="test")

    def test_cross_split_exact_duplicate_is_detected(self):
        dataset = deepcopy(self.dataset)
        row = deepcopy(dataset["records"][0])
        row.update(id="leaked-copy", split="test")
        dataset["records"].append(row)
        report = self.evaluate(dataset, split="test")
        self.assertEqual(report["cross_split_duplicate_documents"], 1)
        self.assertFalse(report["independence_verified"])

    def test_optional_two_rater_agreement(self):
        rows = [{"grades": [3, 0], "ratings": [[3, 0], [3, 0]]}]
        self.assertEqual(weighted_kappa(rows)["quadratic_weighted_kappa"], 1)
        self.assertIsNone(weighted_kappa([{"grades": [0]}]))
        self.assertIsNone(
            weighted_kappa([{"grades": [3], "ratings": [[3], [3]]}])["quadratic_weighted_kappa"]
        )

    def test_live_mode_records_actual_scores_and_fallbacks(self):
        with patch(
            "apps.recruitment.services.ai.router.AIRouter.generate_json",
            return_value=({"score": 0}, "groq", "test-model"),
        ):
            report = self.evaluate(self.dataset, live_ai=True, limit=1)
        self.assertEqual(report["successful_ai_scores"], 2)
        self.assertIsNone(report["external_cost_usd"])
        self.assertEqual(report["score_runs"][0]["snapshot"]["ai"]["score"], 0)
        self.assertIn("hybrid_ai", report["ranking"]["backend"])

    def test_cli_protects_public_report_and_requires_custom_output(self):
        public = settings.BASE_DIR / "docs/evaluation-results.json"
        before = public.read_bytes()
        for options in [
            ["--dataset", ".runtime/private-labels.json"],
            ["--dataset", ".runtime/private-labels.json", "--output", str(public)],
            ["--split", "challenge"],
            ["--live-ai"],
        ]:
            with (
                self.subTest(options=options),
                patch.object(sys, "argv", ["evaluate.py", *options]),
                redirect_stderr(io.StringIO()),
            ):
                with self.assertRaises(SystemExit) as error:
                    runpy.run_path(
                        str(settings.BASE_DIR / "tools/evaluate.py"), run_name="__main__"
                    )
                self.assertEqual(error.exception.code, 2)
        self.assertEqual(public.read_bytes(), before)


class EvaluationAPITests(APITestCase):
    def test_public_benchmark_requires_authentication(self):
        self.assertEqual(self.client.get("/api/evaluation/").status_code, 401)
        self.client.force_authenticate(User.objects.create_user("evaluation-owner"))
        response = self.client.get("/api/evaluation/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["records"], 24)
        self.assertNotIn("text", response.data["cases"][0])

    def test_stale_report_is_not_presented_as_current_dataset(self):
        self.client.force_authenticate(User.objects.create_user("evaluation-owner"))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "evaluation").mkdir()
            (root / "docs").mkdir()
            (root / "evaluation/dataset.json").write_bytes(b"{}")
            (root / "docs/evaluation-results.json").write_bytes(b'{"dataset_sha256":"wrong"}')
            with override_settings(BASE_DIR=root):
                self.assertEqual(self.client.get("/api/evaluation/").status_code, 503)

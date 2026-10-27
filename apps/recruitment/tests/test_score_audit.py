from copy import deepcopy
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APITestCase

from apps.recruitment.models import Analysis, Candidate, Job, ScoreRun
from apps.recruitment.services.matching.audit import reproduce, fingerprint
from apps.recruitment.services.matching.matcher import match_candidate_to_job


class SnapshotArithmeticTests(SimpleTestCase):
    def test_jsonb_numeric_normalization_keeps_fingerprint_stable(self):
        self.assertEqual(
            fingerprint({"score": -0.0, "weight": 1.0}), fingerprint({"score": 0, "weight": 1})
        )

    def test_missing_or_unsupported_snapshot_is_not_guessed(self):
        self.assertFalse(reproduce({})["available"])
        self.assertFalse(reproduce({"schema_version": "future"})["verified"])


class SavedScoringTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user("score-owner")
        self.other = User.objects.create_user("score-other")
        self.client.force_authenticate(self.owner)
        self.candidate = Candidate.objects.create(
            owner=self.owner,
            full_name="Synthetic Example",
            email="synthetic@example.com",
            skills=["Python"],
            years_of_experience=2,
            education="Bachelor of Computer Science",
            analysis_completed=True,
        )
        self.job = Job.objects.create(
            owner=self.owner,
            title="Synthetic role",
            company_name="Lab",
            description="Python Django",
            required_skills=["Python", "Django"],
            minimum_experience=2,
            education_requirement="Bachelor of Computer Science",
        )

    def test_local_snapshot_captures_inputs_and_replays_without_ai(self):
        result = match_candidate_to_job(self.candidate, self.job)
        analysis = Analysis.objects.get(pk=result["analysis_id"])
        self.assertEqual(analysis.scoring_snapshot["rubric"]["score"], 75)
        self.assertIsNone(analysis.scoring_snapshot["ai"]["score"])
        self.assertNotIn("synthetic@example.com", str(analysis.scoring_snapshot))
        with (
            override_settings(
                SKILL_WEIGHT=1,
                EXPERIENCE_WEIGHT=0,
                EDUCATION_WEIGHT=0,
                USE_LLM_FOR_SCORING=True,
                LLM_SCORE_WEIGHT=0.9,
            ),
            patch("requests.post") as post,
        ):
            verified = self.client.get(f"/api/analyses/{analysis.pk}/reproduce/")
        post.assert_not_called()
        self.assertTrue(verified.data["verified"])
        self.assertEqual(verified.data["reproduced_score"], 75)
        self.assertEqual(verified.data["external_requests"], 0)

    @override_settings(USE_LLM_FOR_SCORING=True, LLM_SCORE_WEIGHT=0.25)
    def test_ai_blend_and_zero_score_are_saved_and_reproducible(self):
        for value, expected in [(80, 76.25), (0, 56.25)]:
            with (
                self.subTest(value=value),
                patch(
                    "apps.recruitment.services.ai.router.AIRouter.generate_json",
                    return_value=(
                        {"score": value, "explanation": "Synthetic evidence"},
                        "groq",
                        "test-model",
                    ),
                ) as provider,
            ):
                result = match_candidate_to_job(self.candidate, self.job)
                snapshot = result["scoring_snapshot"]
                self.assertEqual(snapshot["ai"]["score"], value)
                self.assertEqual(snapshot["ai"]["applied_weight"], 0.25)
                self.assertEqual(snapshot["final_score"], expected)
                self.assertTrue(reproduce(snapshot)["verified"])
                provider.assert_called_once()
        self.assertEqual(ScoreRun.objects.count(), 2)

    @override_settings(USE_LLM_FOR_SCORING=True)
    def test_failed_ai_records_zero_applied_weight(self):
        with patch(
            "apps.recruitment.services.ai.router.AIRouter.generate_json",
            return_value=(None, "local", ""),
        ):
            result = match_candidate_to_job(self.candidate, self.job)
        self.assertEqual(result["scoring_snapshot"]["ai"]["applied_weight"], 0)
        self.assertTrue(reproduce(result["scoring_snapshot"])["verified"])

    def test_history_survives_profile_changes_and_new_matches(self):
        first = match_candidate_to_job(self.candidate, self.job)
        original = deepcopy(first["scoring_snapshot"])
        self.candidate.skills = ["Python", "Django"]
        self.candidate.revision += 1
        self.candidate.save()
        second = match_candidate_to_job(self.candidate, self.job)
        self.assertEqual(ScoreRun.objects.get(pk=first["score_run_id"]).snapshot, original)
        self.assertNotEqual(first["score"], second["score"])
        old = self.client.get(f"/api/score-runs/{first['score_run_id']}/reproduce/")
        self.assertTrue(old.data["verified"])
        self.assertEqual(old.data["saved_score"], 75)
        self.assertEqual(
            self.client.get(f"/api/score-runs/?analysis={first['analysis_id']}").data["count"], 2
        )

    def test_tampering_and_changed_saved_total_are_detected(self):
        result = match_candidate_to_job(self.candidate, self.job)
        snapshot = deepcopy(result["scoring_snapshot"])
        snapshot["inputs"]["candidate"]["years"] = 20
        self.assertFalse(reproduce(snapshot)["hash_matches"])
        self.assertFalse(reproduce(snapshot)["verified"])
        self.assertFalse(reproduce(result["scoring_snapshot"], saved_score=1)["verified"])

    def test_history_is_owner_scoped_and_read_only(self):
        result = match_candidate_to_job(self.candidate, self.job)
        run = ScoreRun.objects.get(pk=result["score_run_id"])
        with self.assertRaises(ValidationError):
            run.save()
        self.assertEqual(self.client.post("/api/score-runs/", {}).status_code, 405)
        self.assertEqual(self.client.patch(f"/api/score-runs/{run.pk}/", {}).status_code, 405)
        self.assertEqual(self.client.delete(f"/api/score-runs/{run.pk}/").status_code, 405)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get("/api/score-runs/").data["count"], 0)
        self.assertEqual(self.client.get(f"/api/score-runs/{run.pk}/reproduce/").status_code, 404)
        self.assertEqual(
            self.client.get(f"/api/analyses/{result['analysis_id']}/reproduce/").status_code, 404
        )
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/score-runs/").status_code, 401)

    def test_legacy_analysis_remains_without_fabricated_snapshot(self):
        analysis = Analysis.objects.create(candidate=self.candidate, job=self.job, match_score=88)
        self.assertFalse(
            self.client.get(f"/api/analyses/{analysis.pk}/reproduce/").data["available"]
        )
        self.assertFalse(ScoreRun.objects.exists())

    def test_deleting_candidate_removes_scoring_history(self):
        match_candidate_to_job(self.candidate, self.job)
        self.candidate.delete()
        self.assertFalse(ScoreRun.objects.exists())

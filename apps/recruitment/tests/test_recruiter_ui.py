from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from apps.recruitment.models import Application, Candidate, Job


class ContextualApplicationTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user("context-owner")
        self.client.force_authenticate(self.owner)
        self.candidate = Candidate.objects.create(
            owner=self.owner, full_name="Synthetic Example", email="context@example.com"
        )
        self.first = Job.objects.create(
            owner=self.owner, title="First", company_name="Lab", description="First role"
        )
        self.second = Job.objects.create(
            owner=self.owner, title="Second", company_name="Lab", description="Second role"
        )
        Application.objects.create(candidate=self.candidate, job=self.first)
        Application.objects.create(candidate=self.candidate, job=self.second)

    def test_candidate_workspace_filters_applications_by_both_candidate_and_job(self):
        response = self.client.get(
            "/api/applications/", {"candidate": self.candidate.pk, "job": self.second.pk}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["job"], self.second.pk)
        self.assertEqual(
            self.client.get("/api/applications/", {"candidate": self.candidate.pk}).data["count"], 2
        )

    def test_job_filter_keeps_owner_boundary_and_rejects_invalid_ids(self):
        other = User.objects.create_user("context-other")
        foreign_job = Job.objects.create(
            owner=other, title="Private", company_name="Other", description="Private"
        )
        foreign_candidate = Candidate.objects.create(
            owner=other, full_name="Private", email="other@example.com"
        )
        Application.objects.create(candidate=foreign_candidate, job=foreign_job)
        self.assertEqual(
            self.client.get("/api/applications/", {"job": foreign_job.pk}).data["count"], 0
        )
        self.assertEqual(self.client.get("/api/applications/", {"job": "invalid"}).status_code, 400)

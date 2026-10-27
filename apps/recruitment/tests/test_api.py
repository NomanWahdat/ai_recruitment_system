"""Tests for recruitment API endpoints."""

from rest_framework.test import APITestCase
from rest_framework import status
from apps.recruitment.models import Job, Candidate, Analysis


class OwnedAPITestCase(APITestCase):
    def setUp(self):
        from django.contrib.auth.models import User

        self.user = User.objects.create_user(username="recruiter", password="StrongExample!42")
        self.client.force_authenticate(self.user)


class JobAPITests(OwnedAPITestCase):
    """Test cases for Job API."""

    def test_list_jobs(self):
        """Test listing jobs."""
        Job.objects.create(
            owner=self.user, title="Job 1", company_name="Company A", description="Desc 1"
        )
        Job.objects.create(
            owner=self.user, title="Job 2", company_name="Company B", description="Desc 2"
        )

        response = self.client.get("/api/jobs/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_create_job(self):
        """Test creating a job via API."""
        data = {
            "title": "New Job",
            "company_name": "New Company",
            "description": "Job description",
            "required_skills": ["Python", "Django"],
        }
        response = self.client.post("/api/jobs/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "New Job")

    def test_get_job_detail(self):
        """Test retrieving a single job."""
        job = Job.objects.create(
            owner=self.user, title="Detail Job", company_name="Detail Co", description="Detail desc"
        )
        response = self.client.get(f"/api/jobs/{job.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Detail Job")


class CandidateAPITests(OwnedAPITestCase):
    """Test cases for Candidate API."""

    def test_list_candidates(self):
        """Test listing candidates."""
        Candidate.objects.create(owner=self.user, full_name="Candidate 1", email="c1@example.com")
        Candidate.objects.create(owner=self.user, full_name="Candidate 2", email="c2@example.com")

        response = self.client.get("/api/candidates/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_get_candidate_detail(self):
        """Test retrieving a single candidate."""
        candidate = Candidate.objects.create(
            owner=self.user, full_name="Detail Candidate", email="detail@example.com"
        )
        response = self.client.get(f"/api/candidates/{candidate.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_name"], "Detail Candidate")


class RankingAPITests(OwnedAPITestCase):
    """Test cases for Ranking API."""

    def test_job_rankings(self):
        """Test getting rankings for a job."""
        job = Job.objects.create(
            owner=self.user,
            title="Ranking Test Job",
            company_name="Ranking Co",
            description="Test job",
            required_skills=["Python"],
        )
        candidate = Candidate.objects.create(
            owner=self.user,
            full_name="Rank Candidate",
            email="rank@example.com",
            skills=["Python", "Django"],
        )
        Analysis.objects.create(
            job=job,
            candidate=candidate,
            match_score=85,
            ranking_position=1,
        )

        response = self.client.get(f"/api/jobs/{job.id}/rankings/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["top_candidates"]), 1)
        self.assertEqual(response.data["top_candidates"][0]["match_score"], 85)

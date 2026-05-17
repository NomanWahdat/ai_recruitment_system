"""Tests for recruitment models."""
from django.test import TestCase
from apps.recruitment.models import Job, Candidate


class JobModelTests(TestCase):
    """Test cases for Job model."""

    def test_create_job(self):
        """Test creating a job posting."""
        job = Job.objects.create(
            title="Python Developer",
            company_name="TechCorp",
            location="Remote",
            description="Looking for a Python developer",
            required_skills=["Python", "Django"],
            minimum_experience=3,
        )
        self.assertEqual(job.title, "Python Developer")
        self.assertEqual(job.company_name, "TechCorp")
        self.assertEqual(job.required_skills, ["Python", "Django"])

    def test_job_str_representation(self):
        """Test the string representation of a job."""
        job = Job.objects.create(
            title="Frontend Developer",
            company_name="WebCorp",
            description="Frontend role",
        )
        self.assertEqual(str(job), "Frontend Developer at WebCorp")


class CandidateModelTests(TestCase):
    """Test cases for Candidate model."""

    def test_create_candidate(self):
        """Test creating a candidate profile."""
        candidate = Candidate.objects.create(
            full_name="John Doe",
            email="john@example.com",
            skills=["Python", "React"],
            years_of_experience=5,
        )
        self.assertEqual(candidate.full_name, "John Doe")
        self.assertEqual(candidate.email, "john@example.com")
        self.assertEqual(candidate.skills, ["Python", "React"])

    def test_candidate_default_status(self):
        """Test candidate has default pending status."""
        candidate = Candidate.objects.create(
            full_name="Jane Smith",
            email="jane@example.com",
        )
        self.assertEqual(candidate.processing_status, Candidate.ProcessingStatus.PENDING)

    def test_candidate_str_representation(self):
        """Test the string representation of a candidate."""
        candidate = Candidate.objects.create(
            full_name="Alice Johnson",
            email="alice@example.com",
        )
        self.assertEqual(str(candidate), "Alice Johnson")

import logging
from typing import Dict, Any

from apps.recruitment.models import Candidate, Job
from .agent_orchestrator import orchestrator

logger = logging.getLogger(__name__)


class WorkflowEngine:
    def run_candidate_pipeline(self, candidate: Candidate, source: str = "api") -> Dict[str, Any]:
        logger.info("Running candidate pipeline for candidate_id=%s source=%s", candidate.id, source)
        orchestrator.emit(
            "workflow_triggered",
            {"workflow_type": "candidate", "candidate_id": candidate.id, "source": source},
        )
        return {
            "workflow": "candidate",
            "source": source,
            "events": orchestrator.emit("candidate_created", {"candidate_id": candidate.id, "source": source}),
        }

    def run_job_pipeline(self, job: Job, source: str = "api") -> Dict[str, Any]:
        logger.info("Running job pipeline for job_id=%s source=%s", job.id, source)
        orchestrator.emit(
            "workflow_triggered",
            {"workflow_type": "job", "job_id": job.id, "source": source},
        )
        return {
            "workflow": "job",
            "source": source,
            "events": orchestrator.emit("job_created", {"job_id": job.id, "source": source}),
        }

    def reprocess_all(self) -> Dict[str, Any]:
        candidate_results = []
        job_results = []
        for candidate in Candidate.objects.all().only("id"):
            candidate_results.append(self.run_candidate_pipeline(candidate, source="reprocess"))
        for job in Job.objects.all().only("id"):
            job_results.append(self.run_job_pipeline(job, source="reprocess"))
        return {
            "candidates": len(candidate_results),
            "jobs": len(job_results),
            "candidate_results": candidate_results,
            "job_results": job_results,
        }


workflow_engine = WorkflowEngine()

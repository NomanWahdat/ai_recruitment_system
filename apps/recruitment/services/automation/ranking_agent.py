import logging
from typing import Dict, Any

from apps.recruitment.models import Analysis
from apps.recruitment.services.matching.ranking_engine import top_candidates_for_job
from apps.recruitment.models import Job

logger = logging.getLogger(__name__)


class RankingAgent:
    def handle_match_completed(self, payload: Dict[str, Any]):
        job_id = payload.get("job_id")
        if not job_id:
            return {"job_id": None, "top_candidates": []}
        return self.recalculate(job_id)

    def handle_ranking_requested(self, payload: Dict[str, Any]):
        job_id = payload.get("job_id")
        if not job_id:
            return {"job_id": None, "top_candidates": []}
        return self.recalculate(job_id)

    def recalculate(self, job_id: int):
        logger.info("Recalculating rankings for job_id=%s", job_id)
        # Rankings are recalculated from stored analysis scores.
        # LLM-based refresh is done during matching, not on every rank recalc.
        analyses = list(
            Analysis.objects.select_related("candidate")
            .filter(job_id=job_id)
            .order_by("-match_score", "-analysis_created_at", "id")
        )

        top_candidates = []
        for index, analysis in enumerate(analyses, start=1):
            if analysis.ranking_position != index:
                analysis.ranking_position = index
                analysis.save(update_fields=["ranking_position", "updated_at"])
            if index <= 10:
                top_candidates.append(
                    {
                        "candidate_id": analysis.candidate_id,
                        "match_score": analysis.match_score,
                        "ranking_position": analysis.ranking_position,
                    }
                )

        return {"job_id": job_id, "top_candidates": top_candidates}


ranking_agent = RankingAgent()

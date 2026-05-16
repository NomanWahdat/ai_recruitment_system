import logging
from typing import Dict, Any

from .event_bus import event_bus
from .candidate_agent import candidate_agent
from .job_agent import job_agent
from .ranking_agent import ranking_agent

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    def __init__(self):
        self._wired = False
        self._wire_once()

    def _wire_once(self):
        if self._wired:
            return
        event_bus.subscribe("candidate_created", self._on_candidate_created)
        event_bus.subscribe("candidate_analyzed", self._on_candidate_analyzed)
        event_bus.subscribe("job_created", self._on_job_created)
        event_bus.subscribe("match_completed", self._on_match_completed)
        event_bus.subscribe("ranking_requested", self._on_ranking_requested)
        event_bus.subscribe("workflow_triggered", self._on_workflow_triggered)
        self._wired = True

    def emit(self, event_type: str, payload: Dict[str, Any]):
        logger.info("Emitting event=%s payload_keys=%s", event_type, list((payload or {}).keys()))
        return event_bus.emit(event_type, payload or {})

    def _on_candidate_created(self, payload: Dict[str, Any]):
        logger.info("Dispatching candidate_created")
        return candidate_agent.handle_candidate_created(payload)

    def _on_candidate_analyzed(self, payload: Dict[str, Any]):
        logger.info("Dispatching candidate_analyzed")
        return candidate_agent.handle_candidate_analyzed(payload)

    def _on_job_created(self, payload: Dict[str, Any]):
        logger.info("Dispatching job_created")
        return job_agent.handle_job_created(payload)

    def _on_match_completed(self, payload: Dict[str, Any]):
        logger.info("Dispatching match_completed")
        return ranking_agent.handle_match_completed(payload)

    def _on_ranking_requested(self, payload: Dict[str, Any]):
        logger.info("Dispatching ranking_requested")
        return ranking_agent.handle_ranking_requested(payload)

    def _on_workflow_triggered(self, payload: Dict[str, Any]):
        logger.info("Dispatching workflow_triggered")
        return {"workflow_type": payload.get("workflow_type"), "handled": True}


orchestrator = AgentOrchestrator()

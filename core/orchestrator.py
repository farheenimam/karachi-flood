import uuid
import asyncio
import structlog
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential

from core.state import WorkflowState
from core.config import get_settings
from agents.detector_agent import DetectorAgent
from agents.planner_agent import PlannerAgent
from agents.executor_agent import ExecutorAgent
from models.incident import SignalInput
from models.action import ActionModel
from services.firestore_service import (
    save_incident, save_plan, save_alert, save_trace, log_agent_event
)
from services.websocket_service import ws_manager

logger = structlog.get_logger()
settings = get_settings()


class FloodOrchestrator:
    """
    Orchestrates the multi-agent workflow:
    Detector → Planner → Executor

    Manages state, retries, trace logging, and real-time WebSocket broadcasts.
    Follows Google ADK multi-agent coordination patterns.
    """

    def __init__(self):
        self.detector = DetectorAgent()
        self.planner = PlannerAgent()
        self.executor = ExecutorAgent()

    async def run_workflow(self, signal_input: SignalInput) -> dict:
        session_id = str(uuid.uuid4())
        state = WorkflowState(session_id=session_id)

        logger.info("workflow_started",
            session_id=session_id,
            location=signal_input.location,
        )

        await ws_manager.broadcast_status("started", session_id)
        state.add_trace("Orchestrator", f"Workflow started for {signal_input.location}")

        try:
            result = await self._execute_with_retry(signal_input, state)
            state.status = "completed"
            await ws_manager.broadcast_status("completed", session_id)

        except Exception as e:
            state.status = "failed"
            state.add_error("Orchestrator", str(e))
            logger.error("workflow_failed", session_id=session_id, error=str(e))
            await ws_manager.broadcast_status("failed", session_id)
            result = {"status": "failed", "session_id": session_id, "error": str(e)}

        # Persist full trace
        await save_trace(state)
        await log_agent_event("Orchestrator", "workflow_complete", {
            "session_id": session_id,
            "status": state.status,
            "trace_count": len(state.reasoning_trace),
        })

        return {
            "session_id": session_id,
            "status": state.status,
            "result": result,
            "reasoning_trace": state.reasoning_trace,
            "errors": state.errors,
        }

    async def _execute_with_retry(self, signal_input: SignalInput, state: WorkflowState) -> dict:
        while state.retry_count <= state.max_retries:
            try:
                return await self._pipeline(signal_input, state)
            except Exception as e:
                state.retry_count += 1
                state.add_error(state.current_agent, str(e))
                state.add_trace("Orchestrator",
                    f"Retry {state.retry_count}/{state.max_retries} after error: {str(e)}"
                )
                logger.warning("pipeline_retry",
                    attempt=state.retry_count,
                    agent=state.current_agent,
                    error=str(e),
                )
                if state.retry_count > state.max_retries:
                    raise
                await asyncio.sleep(0.5 * state.retry_count)

        raise RuntimeError("Max retries exceeded")

    async def _pipeline(self, signal_input: SignalInput, state: WorkflowState) -> dict:
        # ─── STAGE 1: DETECTOR ─────────────────────────────────────────────
        state.add_trace("Orchestrator", "Routing to Detector Agent")
        await ws_manager.broadcast_trace("Orchestrator", "Routing to Detector Agent")

        incident = await self.detector.run(signal_input, state)

        # Broadcast detector traces
        for trace in state.reasoning_trace[-5:]:
            if trace["agent"] == "Detector":
                await ws_manager.broadcast_trace(trace["agent"], trace["message"])

        if incident is None:
            state.add_trace("Orchestrator", "No incident detected. Workflow terminated early.")
            await ws_manager.broadcast_trace("Orchestrator",
                f"No incident detected at {signal_input.location}. Classified as false alarm."
            )
            return {
                "status": "no_incident",
                "location": signal_input.location,
                "message": "No flooding detected at this location.",
            }

        await save_incident(incident.model_dump())
        await ws_manager.broadcast_incident(incident.model_dump())
        state.add_trace("Orchestrator",
            f"Incident confirmed: {incident.incident_id[:8]} | Routing to Planner"
        )

        # ─── STAGE 2: PLANNER ──────────────────────────────────────────────
        await ws_manager.broadcast_trace("Orchestrator", "Routing to Planner Agent")

        plan = await self.planner.run(incident, state)

        for trace in state.reasoning_trace[-8:]:
            if trace["agent"] == "Planner":
                await ws_manager.broadcast_trace(trace["agent"], trace["message"])

        if plan is None or not plan.validated:
            state.add_trace("Orchestrator",
                f"Incident invalidated by Planner: {plan.rejected_reason if plan else 'unknown'}"
            )
            await ws_manager.broadcast_trace("Orchestrator",
                f"Incident rejected by Planner: {plan.rejected_reason if plan else 'validation failed'}"
            )
            return {
                "status": "rejected",
                "incident_id": incident.incident_id,
                "reason": plan.rejected_reason if plan else "validation failed",
            }

        await save_plan(plan.model_dump())

        state.add_trace("Orchestrator",
            f"Plan approved: {plan.priority.upper()} priority | Routing to Executor"
        )

        # ─── STAGE 3: EXECUTOR ─────────────────────────────────────────────
        await ws_manager.broadcast_trace("Orchestrator", "Routing to Executor Agent")

        action = await self.executor.run(incident, plan, state)

        for trace in state.reasoning_trace[-6:]:
            if trace["agent"] == "Executor":
                await ws_manager.broadcast_trace(trace["agent"], trace["message"])

        # Build alert object for storage
        alert_record = {
            "incident_id": incident.incident_id,
            "message": action.alert_message,
            "severity": incident.severity,
            "location": incident.location,
            "actions": action.actions,
            "channels": action.alert_channels,
            "ticket_id": action.ticket_id,
            "geofence_km": action.geofence_radius_km,
            "created_at": action.executed_at,
        }
        await save_alert(alert_record)
        await ws_manager.broadcast_alert(alert_record)

        state.add_trace("Orchestrator", "Workflow pipeline complete. All agents finished.")

        return {
            "status": "completed",
            "incident": incident.model_dump(),
            "plan": plan.model_dump(),
            "action": action.model_dump(),
        }

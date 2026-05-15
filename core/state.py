from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime


@dataclass
class WorkflowState:
    session_id: str
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    current_agent: str = "detector"
    status: str = "running"  # running | completed | failed | retrying
    retry_count: int = 0
    max_retries: int = 3

    # Agent outputs
    detector_output: Optional[dict] = None
    planner_output: Optional[dict] = None
    executor_output: Optional[dict] = None

    # Reasoning chain
    reasoning_trace: list[dict] = field(default_factory=list)

    # Error tracking
    errors: list[dict] = field(default_factory=list)

    def add_trace(self, agent: str, message: str, data: Any = None):
        self.reasoning_trace.append({
            "agent": agent,
            "message": message,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def add_error(self, agent: str, error: str):
        self.errors.append({
            "agent": agent,
            "error": error,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "current_agent": self.current_agent,
            "status": self.status,
            "retry_count": self.retry_count,
            "detector_output": self.detector_output,
            "planner_output": self.planner_output,
            "executor_output": self.executor_output,
            "reasoning_trace": self.reasoning_trace,
            "errors": self.errors,
        }

from pydantic import BaseModel, model_validator, Field
from datetime import datetime
from typing import Optional

phases = [
    "not-started", 
    "workload-detection", 
    "workload-selection", 
    "monitoring-plan-generation",
    "monitoring-plan-evaluation", 
    "deployment-confirmation",
    "dashboard-recommendation",
    "alerting-rules-recommendation",
    "completed", 
    "cancelled", 
    "failed"
]

class WorkflowStatus(BaseModel):
    active: bool = False
    thread_id: Optional[str] = None
    phase: Optional[str] = None
    config: Optional[dict] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_access_at: datetime = Field(default_factory=datetime.utcnow)
    last_phase_change_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="after")
    def validate_phase(self):
        if self.phase is not None and self.phase not in phases:
            raise ValueError(f"Phase must be one of {phases}")
        return self

    def touch(self) -> None:
        """Update last access timestamp to current time"""
        self.last_access_at = datetime.utcnow()

    def phase_transition(self, new_phase: str) -> None:
        """Transition to a new phase and update timestamps"""
        if new_phase not in phases:
            raise ValueError(f"Phase must be one of {phases}")
        
        if new_phase != self.phase:
            self.phase = new_phase
            self.last_phase_change_at = datetime.utcnow()
            self.touch()


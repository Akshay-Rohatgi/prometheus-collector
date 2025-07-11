from pydantic import BaseModel, model_validator

phases = ["not-started", "workload-detection", "workload-selection"]

class WorkflowStatus(BaseModel):
    active: bool = False
    thread_id: str = None
    phase: str = None
    config: dict = None

    @model_validator(mode="after")
    def validate_phase(self):
        if self.phase not in phases:
            raise ValueError(f"Phase must be one of {phases}")
        return self

class Workload(BaseModel):
    name: str



from ai.graphs import graph
from core import workflow
from pydantic import BaseModel
from langgraph.types import Command
from fastapi import FastAPI, HTTPException
from utils import printer

app = FastAPI()
workflow_status = workflow.WorkflowStatus(
    active=False,
    phase="not-started",
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the LLM Powered Workload Monitoring API"}

@app.get("/status", response_model=workflow.WorkflowStatus)
def get_workflow_status():
    return workflow_status

# =========================================================
@app.get("/start")
def start_workflow():
    import uuid
    if workflow_status.active:
        raise HTTPException(status_code=400, detail="Workflow already active")

    thread_id=str(uuid.uuid4()),
    config={"configurable": {"thread_id": workflow_status.thread_id}}

    try:
        print("Starting workflow with thread_id:", thread_id)
        workflow_status.phase = "workload-detection"
        result = graph.invoke({}, config=config)

        if "__interrupt__" in result:
            workflow_status.active = True
            workflow_status.thread_id = thread_id
            workflow_status.phase = "workload-selection"
            workflow_status.config = config
            
            return {
                "detected_oss_workloads": result["__interrupt__"][0].value["detected_oss_workloads"],
            }
        else:
            raise HTTPException(status_code=500, detail="Workflow did not return an interrupt")

    except HTTPException as e:
        raise HTTPException(status_code=500, detail=f"Error starting workflow: {str(e)}")

# =========================================================

class selectOssWorkloadsRequest(BaseModel):
    selected_workloads: list[str]

@app.post("/select_oss_workloads")
def select_oss_workloads(request: selectOssWorkloadsRequest):
    if not workflow_status.active:
        raise HTTPException(status_code=400, detail="No active workflow to select workloads")

    selected_workloads_names = request.selected_workloads
    if not selected_workloads_names:
        raise HTTPException(status_code=400, detail="No workloads selected")
    print("Selected OSS workloads:", selected_workloads_names)
    try:
        graph.invoke(
            Command(resume=selected_workloads_names),
            config=workflow_status.config
        )

        return {"message": "Selected OSS workloads successfully", "selected_oss_workloads": selected_workloads_names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error selecting OSS workloads: {str(e)}")

# =========================================================

class generateMonitoringPlanRequest(BaseModel):
    generate: bool = None

@app.post("/generate_monitoring_plan")
def generate_monitoring_plan(request: generateMonitoringPlanRequest):
    # If recievies a "True" resume the workflow
    if not workflow_status.active:
        raise HTTPException(status_code=400, detail="No active workflow to generate monitoring plan")
    
    if request.generate:
        try:
            result = graph.invoke(
                Command(resume=True), # this resumes at "generate_monitoring_deployment_plan"
                config=workflow_status.config
            )

            if "__interrupt__" in result:
                return {"message": "Monitoring deployment plan generated successfully", "monitoring_plans": result["__interrupt__"][0].value["monitoring_plans"]}
            else:
                raise HTTPException(status_code=500, detail="Workflow did not return an interrupt")

        except Exception as e:
            _ = graph.invoke(Command(resume=False), config=workflow_status.config)
            raise HTTPException(status_code=500, detail=f"Error generating monitoring plan: {str(e)}")
    else:
        _ = graph.invoke(Command(resume=False), config=workflow_status.config)
        return {"message": "Monitoring deployment plan generation skipped"}

# =========================================================

class approveMonitoringPlanRequest(BaseModel):
    approval: bool

@app.post("/approve_monitoring_plan")
def approve_monitoring_plan(request: approveMonitoringPlanRequest):
    if not workflow_status.active:
        raise HTTPException(status_code=400, detail="No active workflow to approve monitoring plan")

    if request.approval:
        try:
            graph.invoke(
                Command(resume=request.approval), 
                config=workflow_status.config
            )

            return {"message": "Monitoring deployment plan approved successfully"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error approving monitoring plan: {str(e)}")
    else:
        _ = graph.invoke(Command(resume=False), config=workflow_status.config)
        return {"message": "Monitoring deployment plan not approved, workflow stopped"}

# =========================================================

@app.get("/reset")
def reset_workflow():
    global workflow_status
    workflow_status = workflow.WorkflowStatus(
        active=False,
        phase="not-started",
    )
    return {"message": "Workflow reset successfully"}
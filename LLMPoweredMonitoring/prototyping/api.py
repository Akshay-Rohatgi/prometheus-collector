from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langgraph.types import Command
import nodes
import classes
import uuid

app = FastAPI()

workflow_status = classes.WorkflowStatus(
    active=False,
    phase="not-started",
)

class selectOssWorkloadsRequest(BaseModel):
    selected_workloads: list[str]

@app.get("/status", response_model=classes.WorkflowStatus)
def get_workflow_status():
    return workflow_status

@app.get("/start")
def start_workflow():
    if workflow_status.active:
        raise HTTPException(status_code=400, detail="Workflow already active")

    thread_id=str(uuid.uuid4()),
    config={"configurable": {"thread_id": workflow_status.thread_id}}

    try:
        print("Starting workflow with thread_id:", thread_id)
        workflow_status.phase = "workload-detection"
        result = nodes.graph.invoke({}, config=config)

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

@app.post("/select_oss_workloads")
def select_oss_workloads(request: selectOssWorkloadsRequest):
    if not workflow_status.active:
        raise HTTPException(status_code=400, detail="No active workflow to select workloads")

    selected_workloads_names = request.selected_workloads
    if not selected_workloads_names:
        raise HTTPException(status_code=400, detail="No workloads selected")
    print("Selected OSS workloads:", selected_workloads_names)
    try:
        nodes.graph.invoke(
            Command(resume=selected_workloads_names),
            config=workflow_status.config
        )

        return {"message": "Selected OSS workloads successfully", "selected_oss_workloads": selected_workloads_names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error selecting OSS workloads: {str(e)}")
    
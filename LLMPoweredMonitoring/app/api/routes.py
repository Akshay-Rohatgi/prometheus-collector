from ai.graphs import get_graph
from core import workflow
from pydantic import BaseModel
from langgraph.types import Command
from fastapi import FastAPI, HTTPException
from printer import printer
import uuid
import threading
from typing import Dict

app = FastAPI()

# Thread-safe dictionary to store multiple workflow instances
_workflows: Dict[str, workflow.WorkflowStatus] = {}
_workflows_lock = threading.Lock()

# Store graph instances per workflow to avoid checkpoint conflicts
_workflow_graphs: Dict[str, any] = {}
_graphs_lock = threading.Lock()

def get_workflow_graph(thread_id: str):
    """Get or create a graph instance for a specific workflow"""
    with _graphs_lock:
        if thread_id not in _workflow_graphs:
            _workflow_graphs[thread_id] = get_graph()
        return _workflow_graphs[thread_id]

def cleanup_workflow_graph(thread_id: str):
    """Clean up the graph instance for a workflow"""
    with _graphs_lock:
        if thread_id in _workflow_graphs:
            del _workflow_graphs[thread_id]

@app.get("/")
def read_root():
    return {"message": "Welcome to the LLM Powered Workload Monitoring API"}

@app.get("/status/{thread_id}", response_model=workflow.WorkflowStatus)
def get_workflow_status(thread_id: str):
    with _workflows_lock:
        status = _workflows.get(thread_id)
    if not status:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return status

@app.get("/workflows")
def list_workflows():
    """List all active workflows"""
    with _workflows_lock:
        return {
            "workflows": [
                {"thread_id": tid, "phase": status.phase, "active": status.active}
                for tid, status in _workflows.items()
            ]
        }

# =========================================================
@app.get("/start")
def start_workflow():
    # Generate a proper thread_id (not a tuple!)
    thread_id = str(uuid.uuid4())
    
    # Create new workflow status for this client
    status = workflow.WorkflowStatus(
        active=False,
        phase="not-started",
        thread_id=thread_id
    )
    
    # Store it in our thread-safe dictionary
    with _workflows_lock:
        _workflows[thread_id] = status
    
    config = {"configurable": {"thread_id": thread_id}}

    try:
        printer.info(f"Starting workflow with thread_id: {thread_id}")
        status.phase = "workload-detection"
        status.config = config
        
        # Get workflow-specific graph instance
        workflow_graph = get_workflow_graph(thread_id)
        result = workflow_graph.invoke({}, config=config)

        if "__interrupt__" in result:
            status.active = True
            status.phase = "workload-selection"
            
            return {
                "thread_id": thread_id,
                "detected_oss_workloads": result["__interrupt__"][0].value["detected_oss_workloads"],
            }
        else:
            raise HTTPException(status_code=500, detail="Workflow did not return an interrupt")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting workflow: {str(e)}")

# =========================================================

class selectOssWorkloadsRequest(BaseModel):
    selected_workloads: list[str]

@app.post("/select_oss_workloads/{thread_id}")
def select_oss_workloads(thread_id: str, request: selectOssWorkloadsRequest):
    # Get the workflow status for this specific thread
    with _workflows_lock:
        status = _workflows.get(thread_id)
    
    if not status or not status.active:
        raise HTTPException(status_code=400, detail="No active workflow found for this thread_id")

    selected_workloads_names = request.selected_workloads
    if not selected_workloads_names:
        raise HTTPException(status_code=400, detail="No workloads selected")
    
    printer.info(f"Selected OSS workloads for {thread_id}: {selected_workloads_names}")
    
    try:
        # Get workflow-specific graph instance
        workflow_graph = get_workflow_graph(thread_id)
        workflow_graph.invoke(
            Command(resume=selected_workloads_names),
            config=status.config
        )
        
        status.phase = "monitoring-plan-generation"
        return {"message": "Selected OSS workload successfully", "selected_oss_workload": selected_workloads_names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error selecting OSS workloads: {str(e)}")

# =========================================================

class generateMonitoringPlanRequest(BaseModel):
    generate: bool = None

@app.post("/generate_monitoring_plan/{thread_id}")
def generate_monitoring_plan(thread_id: str, request: generateMonitoringPlanRequest):
    # Get the workflow status for this specific thread
    with _workflows_lock:
        status = _workflows.get(thread_id)
    
    if not status or not status.active:
        raise HTTPException(status_code=400, detail="No active workflow found for this thread_id")
    
    if request.generate:
        try:
            # Get workflow-specific graph instance
            workflow_graph = get_workflow_graph(thread_id)
            result = workflow_graph.invoke(
                Command(resume=True), # this resumes at "generate_monitoring_deployment_plan"
                config=status.config
            )

            if "__interrupt__" in result:
                status.phase = "monitoring-plan-evaluation"
                return {"message": "Monitoring deployment plan generated successfully", "monitoring_plan": result["__interrupt__"][0].value["monitoring_plan"]}
            else:
                raise HTTPException(status_code=500, detail="Workflow did not return an interrupt")

        except Exception as e:
            # Get workflow-specific graph instance for cleanup
            workflow_graph = get_workflow_graph(thread_id)
            _ = workflow_graph.invoke(Command(resume=False), config=status.config)
            raise HTTPException(status_code=500, detail=f"Error generating monitoring plan: {str(e)}")
    else:
        # Get workflow-specific graph instance for cleanup
        workflow_graph = get_workflow_graph(thread_id)
        _ = workflow_graph.invoke(Command(resume=False), config=status.config)
        # Mark workflow as inactive since user chose not to proceed
        status.active = False
        status.phase = "cancelled"
        return {"message": "Monitoring deployment plan generation skipped"}

# =========================================================

class approveMonitoringPlanRequest(BaseModel):
    approval: bool

@app.post("/approve_monitoring_plan/{thread_id}")
def approve_monitoring_plan(thread_id: str, request: approveMonitoringPlanRequest):
    # Get the workflow status for this specific thread
    with _workflows_lock:
        status = _workflows.get(thread_id)
    
    if not status or not status.active:
        raise HTTPException(status_code=400, detail="No active workflow found for this thread_id")

    if request.approval:
        try:
            # Get workflow-specific graph instance
            workflow_graph = get_workflow_graph(thread_id)
            result = workflow_graph.invoke(
                Command(resume=request.approval), 
                config=status.config
            )

            printer.success(f"Monitoring deployment plan approved successfully for {thread_id}")
            status.phase = "deployment-confirmation"

            return {
                "message": "Monitoring deployment plan approved successfully",
                "monitoring_plan": result.get("monitoring_plan"),
                "status": "approved"
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error approving monitoring plan: {str(e)}")
    else:
        # Get workflow-specific graph instance for cleanup
        workflow_graph = get_workflow_graph(thread_id)
        _ = workflow_graph.invoke(Command(resume=False), config=status.config)
        # Mark workflow as inactive since user rejected the plan
        status.active = False
        status.phase = "cancelled"
        return {"message": "Monitoring deployment plan not approved, workflow stopped"}

# =========================================================

class confirmDeploymentRequest(BaseModel):
    approval: bool

@app.post("/confirm_deployment_of_monitoring_plan/{thread_id}")
def confirm_deployment_of_monitoring_plan(thread_id: str, request: confirmDeploymentRequest):
    # Get the workflow status for this specific thread
    with _workflows_lock:
        status = _workflows.get(thread_id)
    
    if not status or not status.active:
        raise HTTPException(status_code=400, detail="No active workflow found for this thread_id")

    if request.approval:
        printer.info(f"Received confirmation to deploy structured monitoring plan for {thread_id}")
        try:
            # Get workflow-specific graph instance
            workflow_graph = get_workflow_graph(thread_id)
            result = workflow_graph.invoke(
                Command(resume=request.approval), 
                config=status.config
            )

            if result.get("deployment_success"):
                # Workflow completed successfully, update status
                status.active = False
                status.phase = "completed"
                # Clean up the graph instance
                cleanup_workflow_graph(thread_id)
                return {
                    "message": "Structured monitoring plan deployed successfully",
                    "status": "deployed",
                    "deployment_success": result.get("deployment_success")
                }
            else:
                status.active = False
                status.phase = "failed"
                cleanup_workflow_graph(thread_id)
                raise HTTPException(status_code=500, detail="Deployment failed!")
        except Exception as e:
            status.active = False
            status.phase = "failed"
            cleanup_workflow_graph(thread_id)
            raise HTTPException(status_code=500, detail=f"Error confirming deployment: {str(e)}")
    else:
        # User rejected deployment, end workflow
        # Get workflow-specific graph instance for cleanup
        workflow_graph = get_workflow_graph(thread_id)
        _ = workflow_graph.invoke(Command(resume=False), config=status.config)
        status.active = False
        status.phase = "cancelled"
        cleanup_workflow_graph(thread_id)
        return {"message": "Deployment of structured monitoring plan not confirmed, workflow stopped"}

@app.delete("/workflow/{thread_id}")
def delete_workflow(thread_id: str):
    """Delete a specific workflow"""
    with _workflows_lock:
        if thread_id in _workflows:
            del _workflows[thread_id]
            # Also clean up the graph instance
            cleanup_workflow_graph(thread_id)
            return {"message": f"Workflow {thread_id} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Workflow not found")

@app.delete("/workflows")
def delete_all_workflows():
    """Delete all workflows"""
    with _workflows_lock:
        count = len(_workflows)
        _workflows.clear()
    # Clean up all graph instances
    with _graphs_lock:
        _workflow_graphs.clear()
    return {"message": f"All {count} workflows deleted successfully"}
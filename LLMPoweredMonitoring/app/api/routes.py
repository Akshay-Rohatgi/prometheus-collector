from ai.graphs import get_graph
from core import workflow
from pydantic import BaseModel
from langgraph.types import Command
from fastapi import FastAPI, HTTPException, Request
from printer import printer
import uuid
import asyncio
import time
from typing import Dict
from logs import get_logger, log_with_context

# Initialize logger
logger = get_logger(__name__)

app = FastAPI()

# Async-safe dictionary to store multiple workflow instances
_workflows: Dict[str, workflow.WorkflowStatus] = {}
_workflows_lock = asyncio.Lock()

# Store graph instances per workflow to avoid checkpoint conflicts
_workflow_graphs: Dict[str, any] = {}
_graphs_lock = asyncio.Lock()

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log HTTP requests with meaningful system information."""
    start_time = time.time()
    
    # Log request start (system event)
    logger.info("HTTP request received", extra={
        'component': 'api',
        'operation': 'request_start',
        'method': request.method,
        'path': str(request.url.path),
        'client_ip': request.client.host if request.client else None,
        'user_agent': request.headers.get('user-agent', 'unknown')
    })
    
    response = await call_next(request)
    
    # Log request completion with metrics (system event)
    duration_ms = round((time.time() - start_time) * 1000, 2)
    logger.info("HTTP request completed", extra={
        'component': 'api',
        'operation': 'request_complete',
        'method': request.method,
        'path': str(request.url.path),
        'status_code': response.status_code,
        'duration_ms': duration_ms,
        'response_size': response.headers.get('content-length', 'unknown')
    })
    
    return response

async def get_workflow_graph(thread_id: str):
    """Get or create a graph instance for a specific workflow"""
    async with _graphs_lock:
        if thread_id not in _workflow_graphs:
            # Run the potentially blocking get_graph() in a thread pool
            _workflow_graphs[thread_id] = await asyncio.to_thread(get_graph)
        return _workflow_graphs[thread_id]

async def cleanup_workflow_graph(thread_id: str):
    """Clean up the graph instance for a workflow"""
    async with _graphs_lock:
        if thread_id in _workflow_graphs:
            del _workflow_graphs[thread_id]

@app.get("/")
async def read_root():
    # Simple endpoint - minimal logging needed
    return {"message": "Welcome to the LLM Powered Workload Monitoring API"}

@app.get("/status/{thread_id}", response_model=workflow.WorkflowStatus)
async def get_workflow_status(thread_id: str):
    async with _workflows_lock:
        status = _workflows.get(thread_id)
    
    if not status:
        # Log workflow lookup failure (system event)
        logger.warning("Workflow status request for non-existent workflow", extra={
            'component': 'api',
            'operation': 'get_workflow_status',
            'thread_id': thread_id,
            'status': 'not_found'
        })
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Log successful status retrieval (system event)
    logger.info("Workflow status retrieved", extra={
        'component': 'api',
        'operation': 'get_workflow_status', 
        'thread_id': thread_id,
        'workflow_phase': status.phase,
        'workflow_active': status.active
    })
    return status

@app.get("/workflows")
async def list_workflows():
    """List all active workflows"""
    async with _workflows_lock:
        workflow_count = len(_workflows)
    
    # Log workflow listing (system event)
    logger.info("Workflows listed", extra={
        'component': 'api',
        'operation': 'list_workflows',
        'active_workflow_count': workflow_count
    })
    async with _workflows_lock:
        return {
            "workflows": [
                {"thread_id": tid, "phase": status.phase, "active": status.active}
                for tid, status in _workflows.items()
            ]
        }

@app.get("/start")
async def start_workflow():
    # Generate a proper thread_id (not a tuple!)
    thread_id = str(uuid.uuid4())
    
    # Log workflow creation (system event)
    logger.info("New workflow requested", extra={
        'component': 'api',
        'operation': 'start_workflow',
        'thread_id': thread_id
    })
    
    # Create new workflow status for this client
    status = workflow.WorkflowStatus(
        active=False,
        phase="not-started",
        thread_id=thread_id
    )
    
    # Store it in our async-safe dictionary
    async with _workflows_lock:
        _workflows[thread_id] = status
    
    config = {"configurable": {"thread_id": thread_id}}

    try:
        printer.info(f"Starting workflow with thread_id: {thread_id}")
        status.phase = "workload-detection"
        status.config = config
        
        # Log phase transition (system event)
        logger.info("Workflow phase transition", extra={
            'component': 'api',
            'operation': 'phase_transition',
            'thread_id': thread_id,
            'from_phase': 'not-started',
            'to_phase': 'workload-detection'
        })
        
        # Get workflow-specific graph instance
        workflow_graph = await get_workflow_graph(thread_id)
        
        # Run the potentially blocking graph.invoke in a thread pool
        result = await asyncio.to_thread(workflow_graph.invoke, {}, config)

        if "__interrupt__" in result:
            status.active = True
            status.phase = "workload-selection"
            
            # Log workflow interruption for user selection (system event)
            logger.info("Workflow interrupted for workload selection", extra={
                'component': 'api',
                'operation': 'workflow_interrupt',
                'thread_id': thread_id,
                'workflow_phase': 'workload-selection',
                'detected_workloads': len(result["__interrupt__"][0].value.get("detected_oss_workloads", []))
            })
            
            return {
                "thread_id": thread_id,
                "detected_oss_workloads": result["__interrupt__"][0].value["detected_oss_workloads"],
            }
        else:
            # Log workflow error (system event)
            logger.error("Workflow did not return expected interrupt", extra={
                'component': 'api',
                'operation': 'workflow_error',
                'thread_id': thread_id,
                'result_keys': list(result.keys()) if isinstance(result, dict) else str(type(result))
            })
            raise HTTPException(status_code=500, detail="Workflow did not return an interrupt")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting workflow: {str(e)}")

# =========================================================

class selectOssWorkloadsRequest(BaseModel):
    selected_workloads: list[str]

@app.post("/select_oss_workloads/{thread_id}")
async def select_oss_workloads(thread_id: str, request: selectOssWorkloadsRequest):
    # Get the workflow status for this specific thread
    async with _workflows_lock:
        status = _workflows.get(thread_id)
    
    if not status or not status.active:
        # Log invalid workflow request (system event)
        logger.warning("OSS workload selection on inactive workflow", extra={
            'component': 'api',
            'operation': 'select_oss_workloads',
            'thread_id': thread_id,
            'workflow_exists': status is not None,
            'workflow_active': status.active if status else False
        })
        raise HTTPException(status_code=400, detail="No active workflow found for this thread_id")

    selected_workloads_names = request.selected_workloads
    if not selected_workloads_names:
        logger.warning("Empty workload selection received", extra={
            'component': 'api',
            'operation': 'select_oss_workloads',
            'thread_id': thread_id
        })
        raise HTTPException(status_code=400, detail="No workloads selected")
    
    # Log workload selection (system event)
    logger.info("OSS workloads selected", extra={
        'component': 'api',
        'operation': 'select_oss_workloads',
        'thread_id': thread_id,
        'selected_workloads': selected_workloads_names,
        'workload_count': len(selected_workloads_names)
    })
    
    printer.info(f"Selected OSS workloads for {thread_id}: {selected_workloads_names}")
    
    try:
        # Get workflow-specific graph instance
        workflow_graph = await get_workflow_graph(thread_id)
        
        # Run the potentially blocking graph.invoke in a thread pool
        await asyncio.to_thread(
            workflow_graph.invoke,
            Command(resume=selected_workloads_names),
            status.config
        )
        
        status.phase = "monitoring-plan-generation"
        
        # Log phase transition (system event)
        logger.info("Workflow advanced to monitoring plan generation", extra={
            'component': 'api',
            'operation': 'select_oss_workloads',
            'thread_id': thread_id,
            'to_phase': 'monitoring-plan-generation'
        })
        
        return {"message": "Selected OSS workload successfully", "selected_oss_workload": selected_workloads_names}
    except Exception as e:
        # Log workflow error (system event)
        logger.error("Error processing workload selection", extra={
            'component': 'api',
            'operation': 'select_oss_workloads',
            'thread_id': thread_id,
            'error': str(e),
            'selected_workloads': selected_workloads_names
        })
        raise HTTPException(status_code=500, detail=f"Error selecting OSS workloads: {str(e)}")

# =========================================================

class generateMonitoringPlanRequest(BaseModel):
    generate: bool = None

@app.post("/generate_monitoring_plan/{thread_id}")
async def generate_monitoring_plan(thread_id: str, request: generateMonitoringPlanRequest):
    # Get the workflow status for this specific thread
    async with _workflows_lock:
        status = _workflows.get(thread_id)
    
    if not status or not status.active:
        raise HTTPException(status_code=400, detail="No active workflow found for this thread_id")
    
    if request.generate:
        try:
            # Get workflow-specific graph instance
            workflow_graph = await get_workflow_graph(thread_id)
            
            # Run the potentially blocking graph.invoke in a thread pool
            result = await asyncio.to_thread(
                workflow_graph.invoke,
                Command(resume=True),  # this resumes at "generate_monitoring_deployment_plan"
                status.config
            )

            if "__interrupt__" in result:
                status.phase = "monitoring-plan-evaluation"
                return {"message": "Monitoring deployment plan generated successfully", "monitoring_plan": result["__interrupt__"][0].value["monitoring_plan"]}
            else:
                raise HTTPException(status_code=500, detail="Workflow did not return an interrupt")

        except Exception as e:
            # Get workflow-specific graph instance for cleanup
            workflow_graph = await get_workflow_graph(thread_id)
            await asyncio.to_thread(workflow_graph.invoke, Command(resume=False), status.config)
            raise HTTPException(status_code=500, detail=f"Error generating monitoring plan: {str(e)}")
    else:
        # Get workflow-specific graph instance for cleanup
        workflow_graph = await get_workflow_graph(thread_id)
        await asyncio.to_thread(workflow_graph.invoke, Command(resume=False), status.config)
        # Mark workflow as inactive since user chose not to proceed
        status.active = False
        status.phase = "cancelled"
        return {"message": "Monitoring deployment plan generation skipped"}

# =========================================================

class approveMonitoringPlanRequest(BaseModel):
    approval: bool

@app.post("/approve_monitoring_plan/{thread_id}")
async def approve_monitoring_plan(thread_id: str, request: approveMonitoringPlanRequest):
    # Get the workflow status for this specific thread
    async with _workflows_lock:
        status = _workflows.get(thread_id)
    
    if not status or not status.active:
        raise HTTPException(status_code=400, detail="No active workflow found for this thread_id")

    if request.approval:
        try:
            # Get workflow-specific graph instance
            workflow_graph = await get_workflow_graph(thread_id)
            
            # Run the potentially blocking graph.invoke in a thread pool
            result = await asyncio.to_thread(
                workflow_graph.invoke,
                Command(resume=request.approval),
                status.config
            )

            printer.success(f"Monitoring deployment plan approved successfully for {thread_id}")
            status.phase = "deployment-confirmation"

            return {
                "message": "Monitoring deployment plan approved successfully",
                "monitoring_plan": result.get("monitoring_plan"),
                "status": "approved"
            }

        except Exception as e:
            import traceback
            printer.error(f"Error approving monitoring plan: {str(e)}")
            printer.error(f"Traceback: {traceback.format_exc()}")
            print(e)
            raise HTTPException(status_code=500, detail=f"Error approving monitoring plan: {str(e)}")
    else:
        # Get workflow-specific graph instance for cleanup
        workflow_graph = await get_workflow_graph(thread_id)
        await asyncio.to_thread(workflow_graph.invoke, Command(resume=False), status.config)
        # Mark workflow as inactive since user rejected the plan
        status.active = False
        status.phase = "cancelled"
        return {"message": "Monitoring deployment plan not approved, workflow stopped"}

# =========================================================

class confirmDeploymentRequest(BaseModel):
    approval: bool

@app.post("/confirm_deployment_of_monitoring_plan/{thread_id}")
async def confirm_deployment_of_monitoring_plan(thread_id: str, request: confirmDeploymentRequest):
    # Get the workflow status for this specific thread
    async with _workflows_lock:
        status = _workflows.get(thread_id)
    
    if not status or not status.active:
        raise HTTPException(status_code=400, detail="No active workflow found for this thread_id")

    if request.approval:
        printer.info(f"Received confirmation to deploy structured monitoring plan for {thread_id}")
        try:
            # Get workflow-specific graph instance
            workflow_graph = await get_workflow_graph(thread_id)
            
            # Run the potentially blocking graph.invoke in a thread pool
            result = await asyncio.to_thread(
                workflow_graph.invoke,
                Command(resume=request.approval),
                status.config
            )

            if result.get("deployment_success"):
                # Move to dashboard recommendation phase instead of completing
                status.phase = "dashboard-recommendation"
                
                return {
                    "message": "Structured monitoring plan deployed successfully",
                    "status": "deployed",
                    "deployment_success": result.get("deployment_success"),
                    "next_phase": "dashboard-recommendation"
                }
            else:
                status.active = False
                status.phase = "failed"
                await cleanup_workflow_graph(thread_id)
                raise HTTPException(status_code=500, detail="Deployment failed!")
        except Exception as e:
            status.active = False
            status.phase = "failed"
            await cleanup_workflow_graph(thread_id)
            raise HTTPException(status_code=500, detail=f"Error confirming deployment: {str(e)}")
    else:
        # User rejected deployment, but continue to dashboard recommendations
        try:
            # Get workflow-specific graph instance
            workflow_graph = await get_workflow_graph(thread_id)
            
            # Continue workflow without deployment
            result = await asyncio.to_thread(workflow_graph.invoke, Command(resume=False), status.config)
            
            # Should now be in dashboard-recommendation phase
            status.phase = "dashboard-recommendation"
            
            return {
                "message": "Deployment skipped, proceeding to dashboard recommendations",
                "status": "deployment-skipped",
                "next_phase": "dashboard-recommendation"
            }
        except Exception as e:
            status.active = False
            status.phase = "failed"
            await cleanup_workflow_graph(thread_id)
            raise HTTPException(status_code=500, detail=f"Error proceeding to dashboard recommendations: {str(e)}")

@app.delete("/workflow/{thread_id}")
async def delete_workflow(thread_id: str):
    """Delete a specific workflow"""
    async with _workflows_lock:
        if thread_id in _workflows:
            del _workflows[thread_id]
            # Also clean up the graph instance
            await cleanup_workflow_graph(thread_id)
            return {"message": f"Workflow {thread_id} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Workflow not found")

@app.delete("/workflows")
async def delete_all_workflows():
    """Delete all workflows"""
    async with _workflows_lock:
        count = len(_workflows)
        _workflows.clear()
    # Clean up all graph instances
    async with _graphs_lock:
        _workflow_graphs.clear()
    return {"message": f"All {count} workflows deleted successfully"}

# =========================================================

class getDashboardRecommendationsRequest(BaseModel):
    get_recommendations: bool

@app.post("/get_dashboard_recommendations/{thread_id}")
async def get_dashboard_recommendations(thread_id: str, request: getDashboardRecommendationsRequest):
    """Get Grafana dashboard recommendations for the deployed monitoring plan"""
    # Get the workflow status for this specific thread
    async with _workflows_lock:
        status = _workflows.get(thread_id)
    
    if not status or not status.active:
        raise HTTPException(status_code=400, detail="No active workflow found for this thread_id")
    
    if status.phase != "dashboard-recommendation":
        raise HTTPException(
            status_code=400, 
            detail=f"Workflow is not in dashboard-recommendation phase. Current phase: {status.phase}"
        )

    try:
        if request.get_recommendations:
            printer.info(f"Generating dashboard recommendations for {thread_id}")
        else:
            printer.info(f"Skipping dashboard recommendations for {thread_id}")
        
        # Get workflow-specific graph instance
        workflow_graph = await get_workflow_graph(thread_id)
        
        # Resume the workflow with user's choice
        result = await asyncio.to_thread(
            workflow_graph.invoke,
            Command(resume=request.get_recommendations),
            status.config
        )

        # Check if the workflow has hit the next interrupt (alerting rules)
        # If the workflow is still active after this invoke, it means it hit another interrupt
        current_state = await asyncio.to_thread(
            workflow_graph.get_state,
            status.config
        )
        
        if current_state.next:  # There are more nodes to execute (hit an interrupt)
            # The workflow continued to alerting rules and is waiting for input
            status.phase = "alerting-rules-recommendation"  
            status.active = True  # Keep workflow active for the next interrupt
        else:
            # Workflow completed successfully, update status
            status.active = False
            status.phase = "completed"
            # Clean up the graph instance
            await cleanup_workflow_graph(thread_id)
        
        if request.get_recommendations:
            recommended_dashboards = result.get("recommended_dashboards", {})
            return {
                "message": "Dashboard recommendations generated successfully",
                "recommended_dashboards": recommended_dashboards,
                "status": status.phase  # Return actual current phase
            }
        else:
            return {
                "message": "Dashboard recommendations skipped" + (", workflow continues to alerting rules" if status.active else ", workflow completed"),
                "status": status.phase  # Return actual current phase
            }

    except Exception as e:
        status.active = False
        status.phase = "failed"
        await cleanup_workflow_graph(thread_id)
        error_message = f"Error processing dashboard recommendations: {str(e)}"
        raise HTTPException(status_code=500, detail=error_message)

# =========================================================

class getAlertingRulesRecommendationsRequest(BaseModel):
    get_recommendations: bool

@app.post("/get_alerting_rules_recommendations/{thread_id}")
async def get_alerting_rules_recommendations(thread_id: str, request: getAlertingRulesRecommendationsRequest):
    """Get Prometheus alerting rules recommendations for the deployed monitoring plan"""
    # Get the workflow status for this specific thread
    async with _workflows_lock:
        status = _workflows.get(thread_id)
    
    if not status or not status.active:
        raise HTTPException(status_code=400, detail="No active workflow found for this thread_id")
    
    if status.phase != "alerting-rules-recommendation":
        raise HTTPException(
            status_code=400, 
            detail=f"Workflow is not in alerting-rules-recommendation phase. Current phase: {status.phase}"
        )

    try:
        if request.get_recommendations:
            printer.info(f"Generating alerting rules recommendations for {thread_id}")
        else:
            printer.info(f"Skipping alerting rules recommendations for {thread_id}")
        
        # Get workflow-specific graph instance
        workflow_graph = await get_workflow_graph(thread_id)
        
        # Resume the workflow with user's choice
        result = await asyncio.to_thread(
            workflow_graph.invoke,
            Command(resume=request.get_recommendations),
            status.config
        )

        # Workflow completed successfully, update status
        status.active = False
        status.phase = "completed"
        # Clean up the graph instance
        await cleanup_workflow_graph(thread_id)
        
        if request.get_recommendations:
            recommended_alerting_rules = result.get("recommended_alerting_rules")
            
            # Convert AlertingRules object to dict for JSON serialization
            if recommended_alerting_rules:
                alerting_rules_dict = {
                    "recommendation": recommended_alerting_rules.recommendation,
                    "generic_recommended_alerting_rules": recommended_alerting_rules.generic_recommended_alerting_rules,
                    "az_compatible_recommended_alerting_rules": recommended_alerting_rules.az_compatible_recommended_alerting_rules
                }
            else:
                alerting_rules_dict = None
                
            return {
                "message": "Alerting rules recommendations generated successfully",
                "recommended_alerting_rules": alerting_rules_dict,
                "status": "completed"
            }
        else:
            return {
                "message": "Alerting rules recommendations skipped, workflow completed",
                "status": "completed"
            }

    except Exception as e:
        status.active = False
        status.phase = "failed"
        await cleanup_workflow_graph(thread_id)
        error_message = f"Error processing alerting rules recommendations: {str(e)}"
        raise HTTPException(status_code=500, detail=error_message)
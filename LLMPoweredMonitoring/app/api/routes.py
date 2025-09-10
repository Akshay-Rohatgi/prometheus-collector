from ai.graphs import get_graph
from ai.tools import fetch_dashboard_from_source
from core import workflow
from pydantic import BaseModel
from langgraph.types import Command
from fastapi import FastAPI, HTTPException, Request
from printer import printer
import uuid
import asyncio
import time
import os
from typing import Dict
from datetime import datetime, timedelta
from collections import OrderedDict
from contextlib import asynccontextmanager
from logs import get_logger, log_with_context

# Initialize logger
logger = get_logger(__name__)

# Workflow lifecycle management configuration
MAX_WORKFLOWS = int(os.getenv("MAX_WORKFLOWS", "7"))
WORKFLOW_TTL_COMPLETED = int(os.getenv("WORKFLOW_TTL_COMPLETED", "600"))  # 10 minutes
WORKFLOW_TTL_FAILED = int(os.getenv("WORKFLOW_TTL_FAILED", "900"))  # 15 minutes
WORKFLOW_TTL_CANCELLED = int(os.getenv("WORKFLOW_TTL_CANCELLED", "300"))  # 5 minutes
WORKFLOW_INACTIVE_TTL = int(os.getenv("WORKFLOW_INACTIVE_TTL", "1800"))  # 30 minutes for idle active workflows
CLEANUP_INTERVAL = int(os.getenv("WORKFLOW_CLEANUP_INTERVAL", "60"))  # 1 minute housekeeping interval
EVICTION_POLICY = os.getenv("EVICTION_POLICY", "lru")  # lru or reject

# Async-safe dictionary to store multiple workflow instances
_workflows: Dict[str, workflow.WorkflowStatus] = {}
_workflows_lock = asyncio.Lock()

# Store graph instances per workflow to avoid checkpoint conflicts
_workflow_graphs: Dict[str, any] = {}
_graphs_lock = asyncio.Lock()

# LRU tracking for workflow access patterns (thread_id -> last_access_timestamp)
_lru_index: OrderedDict[str, datetime] = OrderedDict()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown tasks"""
    # Startup
    housekeeping_task = asyncio.create_task(_housekeeping_cleanup())
    logger.info("Workflow housekeeping task started", extra={
        'component': 'api',
        'operation': 'startup',
        'max_workflows': MAX_WORKFLOWS,
        'cleanup_interval': CLEANUP_INTERVAL
    })
    
    try:
        yield
    finally:
        # Shutdown
        housekeeping_task.cancel()
        try:
            await housekeeping_task
        except asyncio.CancelledError:
            pass
        logger.info("Workflow housekeeping task stopped", extra={
            'component': 'api',
            'operation': 'shutdown'
        })

# Initialize FastAPI with lifespan context manager
app = FastAPI(lifespan=lifespan)

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
            logger.info("Workflow graph cleaned up", extra={
                'component': 'api',
                'operation': 'cleanup_workflow_graph',
                'thread_id': thread_id
            })

def _lru_touch(thread_id: str, status: workflow.WorkflowStatus) -> None:
    """Update LRU index for a workflow"""
    if thread_id in _lru_index:
        _lru_index.move_to_end(thread_id)
    _lru_index[thread_id] = status.last_access_at

def _mark_access(thread_id: str) -> None:
    """Mark a workflow as accessed and update LRU tracking"""
    status = _workflows.get(thread_id)
    if status:
        status.touch()
        _lru_touch(thread_id, status)

def _compute_expired(status: workflow.WorkflowStatus, now: datetime) -> bool:
    """Check if a workflow has expired based on its phase and TTL settings"""
    phase = status.phase
    age = (now - status.last_access_at).total_seconds()
    
    if phase == "completed" and age > WORKFLOW_TTL_COMPLETED:
        return True
    if phase == "failed" and age > WORKFLOW_TTL_FAILED:
        return True
    if phase == "cancelled" and age > WORKFLOW_TTL_CANCELLED:
        return True
    if status.active and age > WORKFLOW_INACTIVE_TTL:
        return True
    
    return False

async def _evict_if_needed() -> None:
    """Evict workflows if we've reached capacity, using LRU + phase-aware strategy"""
    if len(_workflows) < MAX_WORKFLOWS:
        return
    
    now = datetime.utcnow()
    candidates = []
    
    # 1. First priority: expired workflows
    for thread_id, status in _workflows.items():
        if _compute_expired(status, now):
            candidates.append(thread_id)
    
    # 2. Second priority: completed/cancelled/failed workflows (by LRU)
    if not candidates:
        for thread_id in _lru_index:
            status = _workflows.get(thread_id)
            if status and status.phase in ("completed", "cancelled", "failed"):
                candidates.append(thread_id)
                break
    
    # 3. Third priority: any inactive non-terminal workflows
    if not candidates:
        for thread_id in _lru_index:
            status = _workflows.get(thread_id)
            if status and not status.active and status.phase not in ("completed", "cancelled", "failed"):
                candidates.append(thread_id)
                break
    
    # 4. Last resort: idle active workflows over INACTIVITY_TTL
    if not candidates:
        for thread_id in _lru_index:
            status = _workflows.get(thread_id)
            if (status and status.active and 
                (now - status.last_access_at).total_seconds() > WORKFLOW_INACTIVE_TTL):
                logger.warning("Evicting idle active workflow", extra={
                    'component': 'api',
                    'operation': 'evict_idle_active',
                    'thread_id': thread_id,
                    'idle_seconds': (now - status.last_access_at).total_seconds()
                })
                candidates.append(thread_id)
                break
    
    if not candidates:
        if EVICTION_POLICY == "reject":
            raise RuntimeError("Workflow capacity reached; no evictable workflows")
        else:
            # Force evict the oldest workflow as last resort
            oldest_thread_id = next(iter(_lru_index))
            candidates = [oldest_thread_id]
            logger.warning("Force evicting oldest workflow due to capacity", extra={
                'component': 'api',
                'operation': 'force_evict',
                'thread_id': oldest_thread_id
            })
    
    # Evict the selected workflow
    for thread_id in candidates[:1]:  # Only evict one at a time
        status = _workflows.get(thread_id)
        if status and status.active and status.phase not in ("completed", "cancelled", "failed"):
            # Mark as cancelled before eviction
            status.phase_transition("cancelled")
            status.active = False
        
        await cleanup_workflow_graph(thread_id)
        _workflows.pop(thread_id, None)
        _lru_index.pop(thread_id, None)
        
        logger.info("Workflow evicted", extra={
            'component': 'api',
            'operation': 'evict_workflow',
            'thread_id': thread_id,
            'reason': 'capacity_limit',
            'remaining_workflows': len(_workflows)
        })
        break

async def _housekeeping_cleanup() -> None:
    """Background task for periodic TTL-based cleanup"""
    while True:
        try:
            await asyncio.sleep(CLEANUP_INTERVAL)
            
            async with _workflows_lock:
                now = datetime.utcnow()
                to_delete = []
                
                for thread_id, status in _workflows.items():
                    if _compute_expired(status, now):
                        to_delete.append((thread_id, status.phase))
                
                for thread_id, phase in to_delete:
                    await cleanup_workflow_graph(thread_id)
                    _workflows.pop(thread_id, None)
                    _lru_index.pop(thread_id, None)
                    
                    logger.info("Workflow TTL cleanup", extra={
                        'component': 'api',
                        'operation': 'ttl_cleanup',
                        'thread_id': thread_id,
                        'phase': phase,
                        'remaining_workflows': len(_workflows)
                    })
                
        except Exception as e:
            logger.error("Housekeeping task error", extra={
                'component': 'api',
                'operation': 'housekeeping_error',
                'error': str(e)
            })

@app.get("/")
async def read_root():
    # Simple endpoint - minimal logging needed
    return {"message": "Welcome to the LLM Powered Workload Monitoring API"}

@app.get("/status/{thread_id}", response_model=workflow.WorkflowStatus)
async def get_workflow_status(thread_id: str):
    async with _workflows_lock:
        status = _workflows.get(thread_id)
        if status:
            _mark_access(thread_id)
    
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
        'thread_id': thread_id,
        'current_workflow_count': len(_workflows)
    })
    
    async with _workflows_lock:
        # Check capacity and evict if necessary
        try:
            await _evict_if_needed()
        except RuntimeError as e:
            logger.error("Workflow capacity exceeded", extra={
                'component': 'api',
                'operation': 'start_workflow_rejected',
                'thread_id': thread_id,
                'current_workflow_count': len(_workflows),
                'max_workflows': MAX_WORKFLOWS,
                'error': str(e)
            })
            raise HTTPException(status_code=429, detail="Workflow capacity reached; please try again later")
        
        # Create new workflow status for this client
        status = workflow.WorkflowStatus(
            active=False,
            phase="not-started",
            thread_id=thread_id
        )
        
        # Store it in our async-safe dictionary
        _workflows[thread_id] = status
        _mark_access(thread_id)
    
    config = {"configurable": {"thread_id": thread_id}}

    try:
        printer.info(f"Starting workflow with thread_id: {thread_id}")
        status.phase_transition("workload-detection")
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
            status.phase_transition("workload-selection")

            # Extract the interrupt payload produced by the graph (already JSON-safe)
            interrupt_payload = result["__interrupt__"][0].value or {}
            detected_workloads_payload = interrupt_payload.get("detected_oss_workloads", {})

            # Defensive: if values are Pydantic models, normalize; if they are dicts, pass through
            formatted_workloads = {}
            if isinstance(detected_workloads_payload, dict):
                for key, val in detected_workloads_payload.items():
                    if hasattr(val, "name"):  # Workload object
                        formatted_workloads[key] = {
                            "pretty_name": getattr(val, "pretty_name", key),
                            "service_name": val.name,
                            "namespace": val.namespace,
                            "service_type": val.service_type,
                            "ports": val.service_ports,
                        }
                    elif isinstance(val, dict):
                        # Already structured by the workflow; keep as-is
                        formatted_workloads[key] = val
            
            # Log workflow interruption for user selection (system event)
            logger.info("Workflow interrupted for workload selection", extra={
                'component': 'api',
                'operation': 'workflow_interrupt',
                'thread_id': thread_id,
                'workflow_phase': 'workload-selection',
                'detected_workloads': len(formatted_workloads)
            })

            return {
                "thread_id": thread_id,
                "detected_oss_workloads": formatted_workloads,
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
        if status:
            _mark_access(thread_id)
    
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

    selected_workload_keys = request.selected_workloads
    if not selected_workload_keys:
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
        'selected_workload_keys': selected_workload_keys,
        'workload_count': len(selected_workload_keys)
    })
    
    printer.info(f"Selected OSS workloads for {thread_id}: {selected_workload_keys}")
    
    try:
        # Get workflow-specific graph instance
        workflow_graph = await get_workflow_graph(thread_id)
        
        # Run the potentially blocking graph.invoke in a thread pool
        await asyncio.to_thread(
            workflow_graph.invoke,
            Command(resume=selected_workload_keys),
            status.config
        )
        
        status.phase_transition("monitoring-plan-generation")
        
        # Log phase transition (system event)
        logger.info("Workflow advanced to monitoring plan generation", extra={
            'component': 'api',
            'operation': 'select_oss_workloads',
            'thread_id': thread_id,
            'to_phase': 'monitoring-plan-generation'
        })
        
        return {"message": "Selected OSS workload successfully", "selected_oss_workload": selected_workload_keys}
    except Exception as e:
        # Log workflow error (system event)
        logger.error("Error processing workload selection", extra={
            'component': 'api',
            'operation': 'select_oss_workloads',
            'thread_id': thread_id,
            'error': str(e),
            'selected_workloads': selected_workload_keys
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
        if status:
            _mark_access(thread_id)
    
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
                status.phase_transition("monitoring-plan-evaluation")
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
        status.phase_transition("cancelled")
        return {"message": "Monitoring deployment plan generation skipped"}

# =========================================================

class approveMonitoringPlanRequest(BaseModel):
    approval: bool

@app.post("/approve_monitoring_plan/{thread_id}")
async def approve_monitoring_plan(thread_id: str, request: approveMonitoringPlanRequest):
    # Get the workflow status for this specific thread
    async with _workflows_lock:
        status = _workflows.get(thread_id)
        if status:
            _mark_access(thread_id)
    
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
            status.phase_transition("deployment-confirmation")

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
        status.phase_transition("cancelled")
        return {"message": "Monitoring deployment plan not approved, workflow stopped"}

# =========================================================

class confirmDeploymentRequest(BaseModel):
    approval: bool

@app.post("/confirm_deployment_of_monitoring_plan/{thread_id}")
async def confirm_deployment_of_monitoring_plan(thread_id: str, request: confirmDeploymentRequest):
    # Get the workflow status for this specific thread
    async with _workflows_lock:
        status = _workflows.get(thread_id)
        if status:
            _mark_access(thread_id)
    
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
                status.phase_transition("dashboard-recommendation")
                
                return {
                    "message": "Structured monitoring plan deployed successfully",
                    "status": "deployed",
                    "deployment_success": result.get("deployment_success"),
                    "next_phase": "dashboard-recommendation"
                }
            else:
                status.active = False
                status.phase_transition("failed")
                await cleanup_workflow_graph(thread_id)
                raise HTTPException(status_code=500, detail="Deployment failed!")
        except Exception as e:
            status.active = False
            status.phase_transition("failed")
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
            status.phase_transition("dashboard-recommendation")
            
            return {
                "message": "Deployment skipped, proceeding to dashboard recommendations",
                "status": "deployment-skipped",
                "next_phase": "dashboard-recommendation"
            }
        except Exception as e:
            status.active = False
            status.phase_transition("failed")
            await cleanup_workflow_graph(thread_id)
            raise HTTPException(status_code=500, detail=f"Error proceeding to dashboard recommendations: {str(e)}")

@app.delete("/workflow/{thread_id}")
async def delete_workflow(thread_id: str):
    """Delete a specific workflow"""
    async with _workflows_lock:
        if thread_id in _workflows:
            del _workflows[thread_id]
            _lru_index.pop(thread_id, None)
            # Also clean up the graph instance
            await cleanup_workflow_graph(thread_id)
            logger.info("Workflow manually deleted", extra={
                'component': 'api',
                'operation': 'delete_workflow',
                'thread_id': thread_id
            })
            return {"message": f"Workflow {thread_id} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Workflow not found")

@app.delete("/workflows")
async def delete_all_workflows():
    """Delete all workflows"""
    async with _workflows_lock:
        count = len(_workflows)
        _workflows.clear()
        _lru_index.clear()
    # Clean up all graph instances
    async with _graphs_lock:
        _workflow_graphs.clear()
    logger.info("All workflows manually deleted", extra={
        'component': 'api',
        'operation': 'delete_all_workflows',
        'count': count
    })
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
        if status:
            _mark_access(thread_id)
    
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
            status.phase_transition("alerting-rules-recommendation")  
            status.active = True  # Keep workflow active for the next interrupt
        else:
            # Workflow completed successfully, update status
            status.active = False
            status.phase_transition("completed")
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
        status.phase_transition("failed")
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
        if status:
            _mark_access(thread_id)
    
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
        status.phase_transition("completed")
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
        status.phase_transition("failed")
        await cleanup_workflow_graph(thread_id)
        error_message = f"Error processing alerting rules recommendations: {str(e)}"
        raise HTTPException(status_code=500, detail=error_message)


@app.get("/dashboard/{dashboard_id}/json")
async def get_dashboard_json(dashboard_id: str):
    """Fetch dashboard JSON from Grafana.com"""
    try:
        dashboard_json = await fetch_dashboard_from_source(dashboard_id)
        if dashboard_json:
            return {"dashboard": dashboard_json, "dashboard_id": dashboard_id}
        else:
            raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")
    except Exception as e:
        logger.error(f"Error fetching dashboard {dashboard_id}", extra={
            'component': 'api',
            'operation': 'get_dashboard_json',
            'dashboard_id': dashboard_id,
            'error': str(e)
        })
        raise HTTPException(status_code=500, detail=f"Error fetching dashboard: {str(e)}")

@app.get("/metrics/workflows")
async def get_workflow_metrics():
    """Get comprehensive workflow metrics including capacity, phase distribution, and age statistics"""
    async with _workflows_lock:
        total_workflows = len(_workflows)
        now = datetime.utcnow()
        
        # Phase distribution
        phases = {}
        ages = []
        oldest_age = 0
        youngest_age = float('inf')
        expired_count = 0
        active_count = 0
        
        for thread_id, status in _workflows.items():
            # Count by phase
            phases[status.phase] = phases.get(status.phase, 0) + 1
            
            # Age statistics
            age_seconds = (now - status.created_at).total_seconds()
            ages.append(age_seconds)
            
            if age_seconds > oldest_age:
                oldest_age = age_seconds
            if age_seconds < youngest_age:
                youngest_age = age_seconds
                
            # Status counts
            if status.active:
                active_count += 1
                
            if _compute_expired(status, now):
                expired_count += 1
        
        # Compute age percentiles if we have workflows
        percentiles = {}
        if ages:
            ages.sort()
            percentiles = {
                "p50": ages[int(len(ages) * 0.5)] if ages else 0,
                "p90": ages[int(len(ages) * 0.9)] if ages else 0,
                "p95": ages[int(len(ages) * 0.95)] if ages else 0,
                "p99": ages[int(len(ages) * 0.99)] if ages else 0
            }
        
        # Capacity utilization
        capacity_percent = round((total_workflows / MAX_WORKFLOWS) * 100, 2) if MAX_WORKFLOWS > 0 else 0
        
        return {
            "capacity": {
                "current": total_workflows,
                "maximum": MAX_WORKFLOWS,
                "utilization_percent": capacity_percent,
                "available": max(0, MAX_WORKFLOWS - total_workflows)
            },
            "phases": phases,
            "activity": {
                "active": active_count,
                "inactive": total_workflows - active_count,
                "expired": expired_count
            },
            "age_statistics": {
                "oldest_seconds": int(oldest_age),
                "youngest_seconds": int(youngest_age) if youngest_age != float('inf') else 0,
                "percentiles": percentiles
            },
            "configuration": {
                "ttl_completed": WORKFLOW_TTL_COMPLETED,
                "ttl_failed": WORKFLOW_TTL_FAILED,
                "ttl_cancelled": WORKFLOW_TTL_CANCELLED,
                "inactive_ttl": WORKFLOW_INACTIVE_TTL,
                "cleanup_interval": CLEANUP_INTERVAL,
                "eviction_policy": EVICTION_POLICY
            },
            "timestamp": now.isoformat()
        }
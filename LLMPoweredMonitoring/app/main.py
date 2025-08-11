import printer.printer as printer
from dotenv import load_dotenv
from api import routes
import uvicorn
import uuid
import logs


def main():
    # Initialize logging first
    logs.setup_logging()
    logger = logs.get_logger(__name__)
    
    # Log application startup (system event)
    logger.info("Application startup initiated", extra={
        'component': 'main',
        'operation': 'startup',
        'host': '0.0.0.0',
        'port': 8000
    })
    
    # User-facing welcome message (rich output)
    printer.info("Welcome to LLM Powered Workload Monitoring")
    
    try:
        # Log server start attempt
        logger.info("Starting FastAPI server", extra={
            'component': 'main',
            'operation': 'server_start'
        })
        
        uvicorn.run(routes.app, host="0.0.0.0", port=8000)
        
    except Exception as e:
        # Log the error (system event)
        logger.error("Server startup failed", extra={
            'component': 'main',
            'operation': 'startup_error',
            'error_type': type(e).__name__,
            'error_message': str(e)
        })
        
        # Show error to user (rich output)
        printer.error(f"Failed to start server: {e}")
        raise


def k8s():
    from k8s.client import K8sClient, detect_workloads, verify_workloads
    k8s_client = K8sClient("/mnt/c/Users/t-arohatgi/.kube/config")
    workloads = detect_workloads(k8s_client)
    printer.out(workloads)
    # verify_workloads(k8s_client, workloads)


def ai():
    from ai.graphs import graph
    from langgraph.types import Command
    thread_id = str(uuid.uuid4())
    config={"configurable": {"thread_id": thread_id}}
    try:
        result = graph.invoke({}, config=config)

        if "__interrupt__" in result:
            # printer.out("Graph execution was interrupted.")
            # printer.out(result["__interrupt__"][0].value["detected_oss_workloads"])
            pass
    except Exception as e:
        printer.error(f"Graph execution failed: {str(e)}")
        return
    
    input("Select workloads to monitor and press Enter to continue...")
    graph.invoke(Command(resume=["nginx-deployment"]), config=config)

    move_on = input("Would you like to generate a monitoring deployment plan? (yes/no): ").strip().lower()
    if move_on == "yes" or len(move_on) == 0:
        result = graph.invoke(Command(resume=True), config=config)
        printer.out("Monitoring deployment plan generated.")
        printer.out(result)
    else:
        _ = graph.invoke(Command(resume=False), config=config)

    # printer.out(f"Graph result: {result}")


if __name__ == "__main__":
    main()
    #k8s()
    #ai()

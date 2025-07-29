import requests
import rich

from rich.console import Console
from rich.markdown import Markdown

console = Console()

BASE_URL = "http://localhost:8000"

def client_print(message):
    rich.print("[Client]", message)

def check_workflow_status(thread_id):
    """Check and display current workflow status"""
    try:
        response = requests.get(f"{BASE_URL}/status/{thread_id}")
        if response.status_code == 200:
            status = response.json()
            client_print(f"📊 Workflow Status - Phase: {status['phase']}, Active: {status['active']}")
            return status
        else:
            client_print(f"❌ Error getting status: {response.json()}")
            return None
    except Exception as e:
        client_print(f"❌ Error checking status: {e}")
        return None

input("Press Enter to start a new workflow and detect OSS workloads...")

# Start a new workflow and get the thread_id
response = requests.get(f"{BASE_URL}/start")
if response.status_code != 200:
    client_print(f"❌ Error starting workflow: {response.json()}")
    exit(1)

response_with_detected_oss_workloads = response.json()
thread_id = response_with_detected_oss_workloads["thread_id"]
client_print(f"🆔 Workflow started with thread_id: {thread_id}")
client_print(f"Detected OSS workloads: {response_with_detected_oss_workloads['detected_oss_workloads']}")

# Check initial status
check_workflow_status(thread_id)

i = 0
for workload in response_with_detected_oss_workloads["detected_oss_workloads"]:
    client_print(f"{i}. {workload}")
    i += 1

selected_indices = input("Which workloads would you like to select? (comma-separated indices): ").split(",")

selected_workloads = [response_with_detected_oss_workloads["detected_oss_workloads"][int(index.strip())] for index in selected_indices]
response = requests.post(f"{BASE_URL}/select_oss_workloads/{thread_id}", json={"selected_workloads": selected_workloads})
if response.status_code != 200:
    client_print(f"❌ Error selecting workloads: {response.json()}")
    exit(1)
client_print(f"Selected OSS workloads response: {response.json()}")

move_on = input("Would you like to generate a monitoring deployment plan? (yes/no): ").strip().lower()
if move_on == "yes" or len(move_on) == 0:
    response = requests.post(f"{BASE_URL}/generate_monitoring_plan/{thread_id}", json={"generate": True})
    if response.status_code != 200:
        client_print(f"❌ Error generating monitoring plan: {response.json()}")
        exit(1)
    client_print(f"Monitoring deployment plan response")
    monitoring_plan = dict(response.json())['monitoring_plan']
    if monitoring_plan and monitoring_plan.get('markdown_plan'):
        client_print(monitoring_plan['markdown_plan'])
        console.print(Markdown(monitoring_plan['markdown_plan']))
    else:
        client_print("No monitoring plan was generated.")
else:
    exit(0)

approve_plan = input("Do you approve the monitoring deployment plan? (yes/no): ").strip().lower()
if approve_plan == "yes" or len(approve_plan) == 0:
    response = requests.post(f"{BASE_URL}/approve_monitoring_plan/{thread_id}", json={"approval": True})
    if response.status_code != 200:
        client_print(f"❌ Error approving monitoring plan: {response.json()}")
        exit(1)
    monitoring_plan = dict(response.json())['monitoring_plan']
    if monitoring_plan and monitoring_plan.get('structured_plan'):
        console.print("\n[bold cyan]📋 Structured Monitoring Plan:[/bold cyan]")
        console.print("─" * 60)
        
        for i, instruction in enumerate(monitoring_plan['structured_plan'], 1):
            # Handle both old tuple format and new object format
            if isinstance(instruction, dict):
                # New object format - use the type field if available
                instruction_type = instruction.get('type', 'unknown')
                
                if instruction_type == "kubectl":
                    content = instruction['command']
                    display_type = "KubectlCommand"
                    icon = "⚡"
                    color = "bright_blue"
                elif instruction_type == "helm":
                    content = instruction['command']
                    display_type = "HelmCommand"
                    icon = "📦"
                    color = "bright_magenta"
                elif instruction_type == "create_file":
                    content = f"File: {instruction['filename']}\nContent: {instruction['content'][:100]}{'...' if len(instruction['content']) > 100 else ''}"
                    display_type = "CreateFile"
                    icon = "📄"
                    color = "bright_green"
                elif instruction_type == "other":
                    content = f"{instruction['description']}: {instruction['content']}"
                    display_type = instruction['description']
                    icon = "🔧"
                    color = "bright_yellow"
                else:
                    # Fallback for unknown types
                    content = str(instruction)
                    display_type = f"Unknown ({instruction_type})"
                    icon = "❓"
                    color = "bright_red"
            else:
                # Old tuple format (backward compatibility)
                display_type = instruction[0]
                content = instruction[1]
                
                # Color code by instruction type
                if display_type == "KubectlCommand":
                    icon = "⚡"
                    color = "bright_blue"
                elif display_type == "HelmCommand":
                    icon = "📦"
                    color = "bright_magenta"
                elif display_type == "CreateFile":
                    icon = "📄"
                    color = "bright_green"
                else:
                    icon = "🔧"
                    color = "bright_yellow"
            
            console.print(f"\n[bold]{i:2d}. {icon} [{color}]{display_type}[/{color}][/bold]")
            console.print(f"    [dim]┌─[/dim] [green]{content}[/green]")
            console.print(f"    [dim]└─[/dim]")

        
        confirm_deploy = input("\nDo you want to proceed with the automated monitoring deployment? (yes/no): ").strip().lower()
        if confirm_deploy == "yes" or len(confirm_deploy) == 0:
            deployment_response = requests.post(f"{BASE_URL}/confirm_deployment_of_monitoring_plan/{thread_id}", json={"approval": True})
            if deployment_response.status_code == 200:
                result = deployment_response.json()
                client_print(f"✅ {result['message']}")
                if result.get("deployment_success"):
                    client_print("🚀 Monitoring deployment completed successfully!")
                else:
                    client_print("❌ Deployment was not successful.")
            else:
                client_print(f"❌ Error during deployment confirmation: {deployment_response.json()}")
        else:
            # Send rejection to stop the workflow
            requests.post(f"{BASE_URL}/confirm_deployment_of_monitoring_plan/{thread_id}", json={"approval": False})
            client_print("❌ Automated monitoring deployment cancelled.")
    else:
        client_print("❌ No structured plan available for deployment.")
else:
    # Send rejection to stop the workflow
    requests.post(f"{BASE_URL}/approve_monitoring_plan/{thread_id}", json={"approval": False})
    client_print("❌ Monitoring deployment plan not approved, workflow stopped.")

# Offer to clean up the workflow
cleanup = input(f"\nWould you like to delete this workflow ({thread_id})? (yes/no): ").strip().lower()
if cleanup == "yes":
    delete_response = requests.delete(f"{BASE_URL}/workflow/{thread_id}")
    if delete_response.status_code == 200:
        client_print("🗑️ Workflow deleted successfully.")
    else:
        client_print(f"❌ Error deleting workflow: {delete_response.json()}")
else:
    client_print(f"ℹ️ Workflow {thread_id} preserved. You can check its status at: {BASE_URL}/status/{thread_id}")
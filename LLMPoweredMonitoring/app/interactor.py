import requests
import rich

from rich.console import Console
from rich.markdown import Markdown

console = Console()

BASE_URL = "http://localhost:8000"

_ = requests.get(f"{BASE_URL}/reset")

def client_print(message):
    rich.print("[Client]", message)

response = requests.get(f"{BASE_URL}/status")
status_data = response.json()
client_print(f"Status response: {status_data}")

input("Press Enter to detect OSS workloads...")

response = requests.get(f"{BASE_URL}/start")
response_with_detected_oss_workloads = response.json()
client_print(f"Detected OSS workloads: {response_with_detected_oss_workloads}")

i = 0
for workload in response_with_detected_oss_workloads["detected_oss_workloads"]:
    client_print(f"{i}. {workload}")
    i += 1

selected_indices = input("Which workloads would you like to select? (comma-separated indices): ").split(",")

selected_workloads = [response_with_detected_oss_workloads["detected_oss_workloads"][int(index.strip())] for index in selected_indices]
response = requests.post(f"{BASE_URL}/select_oss_workloads", json={"selected_workloads": selected_workloads})
client_print(f"Selected OSS workloads response: {response.json()}")

move_on = input("Would you like to generate a monitoring deployment plan? (yes/no): ").strip().lower()
if move_on == "yes" or len(move_on) == 0:
    response = requests.post(f"{BASE_URL}/generate_monitoring_plan", json={"generate": True})
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
    response = requests.post(f"{BASE_URL}/approve_monitoring_plan", json={"approval": True})
    monitoring_plan = dict(response.json())['monitoring_plan']
    if monitoring_plan and monitoring_plan.get('structured_plan'):
        console.print("\n[bold cyan]📋 Structured Monitoring Plan:[/bold cyan]")
        console.print("─" * 60)
        
        for i, instruction in enumerate(monitoring_plan['structured_plan'], 1):
            instruction_type = instruction[0]
            content = instruction[1]
            
            # Color code by instruction type
            if instruction_type == "KubectlCommand":
                icon = "⚡"
                color = "bright_blue"
            elif instruction_type == "HelmCommand":
                icon = "📦"
                color = "bright_magenta"
            elif instruction_type == "CreateFile":
                icon = "📄"
                color = "bright_green"
            else:
                icon = "🔧"
                color = "bright_yellow"
            
            console.print(f"\n[bold]{i:2d}. {icon} [{color}]{instruction_type}[/{color}][/bold]")
            console.print(f"    [dim]┌─[/dim] [green]{content}[/green]")
            console.print(f"    [dim]└─[/dim]")

        
        confirm_deploy = input("\nDo you want to proceed with the automated monitoring deployment? (yes/no): ").strip().lower()
        if confirm_deploy == "yes" or len(confirm_deploy) == 0:
            deployment_response = requests.post(f"{BASE_URL}/confirm_deployment_of_monitoring_plan", json={"approval": True})
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
            requests.post(f"{BASE_URL}/confirm_deployment_of_monitoring_plan", json={"approval": False})
            client_print("❌ Automated monitoring deployment cancelled.")
    else:
        client_print("❌ No structured plan available for deployment.")
else:
    # Send rejection to stop the workflow
    requests.post(f"{BASE_URL}/approve_monitoring_plan", json={"approval": False})
    client_print("❌ Monitoring deployment plan not approved, workflow stopped.")
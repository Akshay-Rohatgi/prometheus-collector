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

approve = input("Do you approve the monitoring deployment plan? (yes/no): ").strip().lower()
if approve == "yes" or len(approve) == 0:
    response = requests.post(f"{BASE_URL}/approve_monitoring_plan", json={"approval": True})
    monitoring_plan = dict(response.json())['monitoring_plan']
    if monitoring_plan and monitoring_plan.get('structured_plan'):
        # rich.print(monitoring_plan['structured_plan'])
        for instruction in monitoring_plan['structured_plan']:
            print("")
            client_print(f"Type: {instruction[0]}, Content: {instruction[1]}")
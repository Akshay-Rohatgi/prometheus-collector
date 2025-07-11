import requests
import rich

BASE_URL = "http://localhost:8000"

response = requests.get(f"{BASE_URL}/status")
status_data = response.json()
rich.print(f"Status response: {status_data}")

input("Press Enter to detect OSS workloads...")

response = requests.get(f"{BASE_URL}/start")
response_with_detected_oss_workloads = response.json()
rich.print(f"Detected OSS workloads: {response_with_detected_oss_workloads}")

i = 0
for workload in response_with_detected_oss_workloads["detected_oss_workloads"]:
    rich.print(f"{i}. {workload}")
    i += 1

selected_indices = input("Which workloads would you like to select? (comma-separated indices): ").split(",")

selected_workloads = [response_with_detected_oss_workloads["detected_oss_workloads"][int(index.strip())] for index in selected_indices]
response = requests.post(f"{BASE_URL}/select_oss_workloads", json={"selected_workloads": selected_workloads})
rich.print(f"Selected OSS workloads response: {response.json()}")

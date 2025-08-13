from deepeval.test_case import LLMTestCase
from deepeval import evaluate, assert_test
from tests.ai.metrics.oss_detection import (
    get_all_oss_detection_metrics,
    create_oss_detection_e2e_test_case,
    create_oss_detection_reasoning_test_case,
    create_oss_detection_tool_usage_test_case
)
from k8s.client import Workload
from ai.graphs import detect_oss_workloads, Workflow
import json

valid_workloads_akshay_cluster = [
    {"Kafka": ["my-cluster-kafka-bootstrap", "my-cluster-kafka-brokers"]},
    {"PostgreSQL": ["postgres"]},
    {"RabbitMQ": ["hello-world"]},
    {"nginx": ["nginx-service"]},
    {"MySQL": ["mysql"]},
    {"Elasticsearch": ["quickstart-es-http", "quickstart-es-default", "quickstart-es-internal-http"]},
]

def json_dump_to_workloads(json_file: str) ->  dict[str, Workload]:
    detected_workloads = {}

    with open(json_file, "r") as f:
        data = json.load(f)

    for name, workload_data in data.items():
        detected_workloads[name] = Workload(
            name=name,
            namespace=workload_data["namespace"],
            metadata_name=workload_data["metadata_name"],
            metadata_labels=workload_data["metadata_labels"],
            service_type=workload_data.get("service_type", "ClusterIP"),
            service_ports=workload_data.get("service_ports", []),
            service_annotations=workload_data.get("service_annotations", {}),
        )

    return detected_workloads


def test_oss_detection():
    """Run end-to-end evaluation of OSS detection"""
    print("🚀 Starting OSS detection e2e evaluation...")

    metrics = get_all_oss_detection_metrics()

    # create a minimal workflow state for testing
    detected_workloads = json_dump_to_workloads(
        "fixtures/workloads.json"
    )
    workflow = Workflow(
        detected_workloads=detected_workloads
    )

    state = detect_oss_workloads(workflow)
    detected_oss_workloads = state.get("detected_oss_workloads")
    detected_oss_workloads = [name for name, _ in detected_oss_workloads.items()]

    oss_detection_e2e_test = create_oss_detection_e2e_test_case(
        valid_workloads_akshay_cluster, 
        detected_oss_workloads
    )
    oss_detection_reasoning_test = create_oss_detection_reasoning_test_case(
        input="Detect OSS workloads in the cluster",
        output=workflow.oss_detection_reasoning
    )
    oss_detection_tool_usage_test = create_oss_detection_tool_usage_test_case(
        input="Detect OSS workloads in the cluster",
        tool_calls=workflow.oss_detection_tool_calls
    )

    test_cases = [oss_detection_e2e_test, oss_detection_reasoning_test, oss_detection_tool_usage_test]

    print(f"📈 Running evaluation with {len(metrics)} metric(s)...")

    # Test the OSS Minimum Detection Metric
    assert_test(oss_detection_e2e_test, [metrics[0]])
    # Test the OSS Detection Reasoning Metric
    assert_test(oss_detection_reasoning_test, [metrics[1]])
    # Test the OSS Detection Tool Usage Metric
    assert_test(oss_detection_tool_usage_test, [metrics[2]])


if __name__ == "__main__":
    test_oss_detection()
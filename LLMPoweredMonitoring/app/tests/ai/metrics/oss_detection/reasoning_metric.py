"""OSS Detection Reasoning Metric

This module contains the GEval metric for evaluating the quality of OSS detection reasoning.
"""

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams


def create_oss_detection_reasoning_metric() -> GEval:
    """G-Eval metric for OSS detection reasoning quality."""
    return GEval(
        name="OSS Detection Reasoning",
        criteria="Evaluate the quality and accuracy of OSS workload detection reasoning based on systematic analysis methodology",
        evaluation_steps=[
            "Verify that service name analysis correctly identifies well-known OSS project patterns (kafka, elasticsearch, redis, etc.) and properly excludes exporters/metrics services",
            "Check that namespace analysis appropriately weighs dedicated OSS namespaces as positive signals while treating default namespace neutrally",
            "Assess if labels and annotations analysis properly identifies OSS indicators like Helm charts, operator annotations, and project-specific labels",
            "Validate that port and protocol analysis correctly recognizes well-known OSS service ports and protocols (9092 for Kafka, 5672 for RabbitMQ, etc.)",
            "Ensure confidence levels (HIGH/MEDIUM/LOW) are appropriately assigned based on strength of evidence and clarity of OSS identification",
            "Confirm that exclusion criteria are properly applied to filter out system components, cloud provider services, and support infrastructure",
            "Verify focus on core services rather than exporters, controllers, or monitoring components"
        ],
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT]
    )

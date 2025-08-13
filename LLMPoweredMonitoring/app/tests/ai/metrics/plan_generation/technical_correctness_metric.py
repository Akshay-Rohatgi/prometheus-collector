"""Plan Generation Technical Correctness Metric

This module contains the GEval metric for evaluating technical correctness of monitoring plans.
"""

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams


def create_plan_technical_correctness_metric() -> GEval:
    """G-Eval metric for technical correctness of monitoring plans."""
    return GEval(
        name="Technical Correctness", 
        criteria="Evaluate the technical accuracy of Helm commands, Kubernetes configurations, and monitoring setup instructions",
        evaluation_steps=[
            "Verify Helm chart names and versions are correct and realistic",
            "Check that Kubernetes resource names follow proper naming conventions", 
            "Validate that service URIs are properly formatted",
            "Ensure required configuration parameters are included with appropriate placeholder values",
            "Assess if security best practices are followed (no hardcoded secrets)"
        ],
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT]
    )

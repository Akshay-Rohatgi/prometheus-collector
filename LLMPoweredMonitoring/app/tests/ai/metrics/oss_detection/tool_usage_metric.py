from deepeval.metrics import ArgumentCorrectnessMetric
from deepeval.test_case import LLMTestCase

def create_tool_usage_metric() -> ArgumentCorrectnessMetric:
    """LLM-As-A-Judge metric for determining correct tool usage."""
    return ArgumentCorrectnessMetric(
        threshold=0.9,
        include_reason=True,
        # strict_mode=True
    )
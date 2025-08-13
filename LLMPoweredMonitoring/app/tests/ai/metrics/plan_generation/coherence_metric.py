"""Plan Generation Coherence Metric

This module contains the GEval metric for evaluating monitoring plan coherence.
"""

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams


def create_plan_coherence_metric() -> GEval:
    """G-Eval metric for monitoring plan generation coherence."""
    return GEval(
        name="Plan Coherence",
        criteria="Evaluate the monitoring plan for format coherence, prerequisite ordering, and proper step categorization",
        evaluation_steps=[
            "Check if the plan follows established markdown format patterns with proper headers and sections",
            "Verify that prerequisites are clearly identified and come before dependent steps", 
            "Ensure unnecessary or optional steps are explicitly marked as optional",
            "Validate that the plan includes all essential monitoring components (exporter, service monitor, configuration)",
            "Assess if the plan is logically structured and easy to follow"
        ],
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT]
    )

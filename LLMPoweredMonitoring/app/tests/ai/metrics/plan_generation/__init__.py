"""Plan Generation Metrics Module

This module provides all metrics and test case creation functions for evaluating
monitoring plan generation functionality.
"""

from .coherence_metric import create_plan_coherence_metric
from .technical_correctness_metric import create_plan_technical_correctness_metric
from .test_cases import (
    create_plan_generation_test_case,
    create_simple_plan_generation_test_case
)

def get_all_plan_generation_metrics():
    """Factory function to get all plan generation metrics.
    
    Returns:
        list: List of all plan generation metrics (GEval metrics)
    """
    return [
        create_plan_coherence_metric(),
        create_plan_technical_correctness_metric()
    ]

__all__ = [
    'create_plan_coherence_metric',
    'create_plan_technical_correctness_metric', 
    'create_plan_generation_test_case',
    'create_simple_plan_generation_test_case',
    'get_all_plan_generation_metrics'
]

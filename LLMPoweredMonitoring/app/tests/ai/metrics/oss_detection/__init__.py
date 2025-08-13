"""OSS Detection Metrics Module

This module provides all metrics and test case creation functions for evaluating
OSS workload detection functionality.
"""

from .accuracy_metric import MinimumNumOfOSSDetectionMetric
from .reasoning_metric import create_oss_detection_reasoning_metric
from .tool_usage_metric import create_tool_usage_metric
from .test_cases import (
    create_oss_detection_e2e_test_case,
    create_oss_detection_reasoning_test_case,
    create_oss_detection_tool_usage_test_case
)

def get_all_oss_detection_metrics():
    """Factory function to get all OSS detection metrics.
    
    Returns:
        list: List of all OSS detection metrics (both quantitative and qualitative)
    """
    return [
        MinimumNumOfOSSDetectionMetric(),
        create_oss_detection_reasoning_metric(),
        create_tool_usage_metric()
    ]

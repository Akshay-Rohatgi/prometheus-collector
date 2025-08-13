"""OSS Detection Accuracy Metric

This metric evaluates the agent responsible for detecting which workloads are OSS.
To compute the score of the agent's response, we need to check if the detected workloads 
match the valid workloads. However, multiple "Workload objects" can be valid for a single 
workload. The computation will iterate through the list of valid workloads, checking if 
at least one of their associated valid workload objects is present in the detected workloads. 
If so, it counts as a valid detection. There are n valid detections per dataset, and the 
score will be valid_detections / n.
"""

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class MinimumNumOfOSSDetectionMetric(BaseMetric):
    """Quantitative metric to evaluate OSS workload detection accuracy."""
    
    def __init__(self, threshold: float = 1.0):
        self.threshold = threshold

    async def compute_score(self, valid_workloads: list[dict[str, list[str]]], detected_oss_workload_names: list[str]) -> float:
        """Compute the detection accuracy score."""
        valid_detections = 0
        n = len(valid_workloads)
        
        for valid in valid_workloads:
            for workload_name, valid_workload_objects in valid.items():
                # Check if any of the valid workload objects are in the detected names
                if any(obj in detected_oss_workload_names for obj in valid_workload_objects):
                    valid_detections += 1
                    break

        return valid_detections / n if n > 0 else 0

    def measure(self, test_case: LLMTestCase) -> float:
        """Synchronous measure method required by deepeval."""
        try:
            self.score = self.compute_score(
                test_case.additional_metadata.get("valid_workloads", []), 
                test_case.additional_metadata.get("detected_oss_workload_names", [])
            )
            self.success = self.score >= self.threshold
        except Exception as e:
            self.error = str(e)
            raise

    async def a_measure(self, test_case: LLMTestCase) -> float:
        """Asynchronous measure method required by deepeval."""
        try:
            self.score = await self.compute_score(
                test_case.additional_metadata.get("valid_workloads", []), 
                test_case.additional_metadata.get("detected_oss_workload_names", [])
            )
            self.success = self.score >= self.threshold
        except Exception as e:
            self.error = str(e)
            raise

    def is_successful(self) -> bool:
        """Check if the metric passed the threshold."""
        if self.score < self.threshold:
            return False
        return self.success

    @property
    def __name__(self):
        return "Minimum OSS Detection Metric"

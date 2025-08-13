"""OSS Detection Test Case Creation Functions

This module contains all test case creation functions for OSS detection testing.
"""

from deepeval.test_case import LLMTestCase, ToolCall


def create_oss_detection_e2e_test_case(valid_workloads, detected_workloads) -> LLMTestCase:
    """Create test case for end-to-end OSS detection accuracy evaluation.
    
    Args:
        valid_workloads: Expected OSS workloads from ground truth
        detected_workloads: Actual detected OSS workload names
        
    Returns:
        LLMTestCase: Test case with metadata for accuracy metric evaluation
    """
    return LLMTestCase(
        input="Detect OSS workloads in the cluster",
        additional_metadata={
            "valid_workloads": valid_workloads,
            "detected_oss_workload_names": detected_workloads
        },
    )


def create_oss_detection_reasoning_test_case(input, output) -> LLMTestCase:
    """Create test case for OSS detection reasoning quality evaluation.
    
    Args:
        input: The input prompt given to the OSS detection agent
        output: The reasoning output from the OSS detection agent
        
    Returns:
        LLMTestCase: Test case for GEval reasoning metric evaluation
    """
    return LLMTestCase(
        input=input,
        actual_output=output,
    )

def create_oss_detection_tool_usage_test_case(input, tool_calls) -> LLMTestCase:
    """Create test case for OSS detection tool usage evaluation.

    Args:
        input: The input prompt given to the OSS detection agent
        output: The tool usage output from the OSS detection agent

    Returns:
        LLMTestCase: Test case for tool usage metric evaluation
    """

    tool_calls_formatted_for_deepeval = []
    for tool_call in tool_calls:
        tool_calls_formatted_for_deepeval.append(ToolCall(
            name=tool_call["name"],
            description="Tool to add workload name to list of detected OSS workloads",
            input_parameters=tool_call["args"]
        ))

    return LLMTestCase(
        input=input,
        tools_called=tool_calls_formatted_for_deepeval
    )
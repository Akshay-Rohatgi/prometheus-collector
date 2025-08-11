"""Utilities for printing and formatting output."""

from printer import printer
from langchain_community.callbacks import get_openai_callback
from logs import get_logger

logger = get_logger(__name__)

def print_token_stats(callback: get_openai_callback) -> None:
    """Print token usage and cost statistics from an OpenAI callback."""
    printer.banner("AI Agent Tokens and Cost")
    printer.out(
        f"💵 Total tokens used: {callback.total_tokens}\n"
        + f"💵 Prompt tokens: {callback.prompt_tokens}\n"
        + f"💵 Completion tokens: {callback.completion_tokens}\n"
        + f"💵 Total cost: ${callback.total_cost:.6f}"
    )
    logger.info(f"Total tokens used: {callback.total_tokens}\n"
                f"Prompt tokens: {callback.prompt_tokens}\n"
                f"Completion tokens: {callback.completion_tokens}\n"
                f"Total cost: ${callback.total_cost:.6f}", extra={
                    'component': 'workflow',
                    'operation': 'record_token_stats'
                })

    printer.banner("AI Agent Tokens and Cost")

def print_workload_list(title: str, workloads: dict, emoji: str = "🔨") -> None:
    """Print a formatted list of workloads with a title and emoji.

    Args:
        title: The title to display in the banner
        workloads: Dictionary of workloads to display
        emoji: The emoji to use for each workload (default: 🔨)
    """
    printer.banner(title)
    printer.out(
        "\n".join(
            f"{emoji} {name} in {workload.namespace}"
            for name, workload in workloads.items()
        )
    )
    printer.banner(title)

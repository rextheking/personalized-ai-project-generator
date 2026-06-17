"""The Personalized AI Project Generator agent, built with Strands Agents SDK."""

import os

from strands import Agent
from strands.models import BedrockModel

from .prompts import SYSTEM_PROMPT
from .tools import build_implementation_plan, generate_project_ideas

# Model id can be overridden with an environment variable so you can switch
# models without touching code. Defaults to the Claude Sonnet 4 cross-region
# inference profile on Bedrock. Newer Claude models require the inference
# profile id (the "us." prefix) rather than the bare model id.
DEFAULT_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0"
)
DEFAULT_REGION = os.environ.get("AWS_REGION", "us-east-1")


def build_agent(callback_handler=None) -> Agent:
    """Create and return a configured project generator agent.

    Args:
        callback_handler: Optional Strands callback handler. Pass None to keep
            the agent quiet, which is what we want inside Lambda.

    Returns:
        A ready to use Strands Agent.
    """
    model = BedrockModel(
        model_id=DEFAULT_MODEL_ID,
        region_name=DEFAULT_REGION,
        temperature=0.4,
    )

    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[generate_project_ideas, build_implementation_plan],
        callback_handler=callback_handler,
    )


def ask(prompt: str) -> str:
    """Run a single prompt through the agent and return the text response.

    This is a convenience wrapper for one-shot calls from the web backend.
    """
    agent = build_agent(callback_handler=None)
    result = agent(prompt)
    return str(result)

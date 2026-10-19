from google.adk import Agent

from .prompt import get_instruction

conversion_agent = Agent(
    name="ConversionAgent",
    model="gemini-2.5-flash-lite",
    description="basic agent",
    instruction=get_instruction,
)

root_agent = conversion_agent
